from __future__ import annotations

import httpx


class LocalCoderProvider:
    """OpenAI-compatible local HTTP provider.

    Retained for environments where a local inference server such as
    vLLM is available.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000/v1",
        model: str = "Qwen/Qwen3-8B",
        timeout: int = 180,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def complete(
        self,
        system: str,
        user: str,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": system,
                },
                {
                    "role": "user",
                    "content": user,
                },
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        response = httpx.post(
            self.base_url + "/chat/completions",
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()

        return response.json()["choices"][0]["message"]["content"]


_NATIVE_BMM_DISABLED = False


def _configure_office_cuda_compatibility() -> None:
    """Avoid the PyTorch native Triton BMM path on managed WSL.

    PyTorch 2.13 may route BMM operations through a Triton implementation
    which JIT-compiles a helper requiring Python development headers.

    Managed office systems may not expose those headers and may not allow
    sudo installation. Disabling only this native override keeps the
    standard CUDA/PyTorch implementation available.
    """

    global _NATIVE_BMM_DISABLED

    if _NATIVE_BMM_DISABLED:
        return

    try:
        from torch._native.registry import deregister_op_overrides

        deregister_op_overrides(
            disable_op_symbols="bmm",
        )
    except (
        ImportError,
        AttributeError,
    ):
        # Older/newer PyTorch releases may not expose this private
        # compatibility hook. In those environments nothing is changed.
        pass

    _NATIVE_BMM_DISABLED = True


class TransformersCoderProvider:
    """Direct local Transformers provider.

    No inference server, paid API, administrator privilege, vLLM, or
    Accelerate installation is required.
    """

    def __init__(
        self,
        model: str = "Qwen/Qwen3-8B",
        device: str = "cuda",
        max_context_tokens: int = 8192,
    ) -> None:
        self.model_name = model
        self.device = device
        self.max_context_tokens = max_context_tokens

        self._tokenizer = None
        self._model = None

    def _load(self) -> None:
        if self._model is not None:
            return

        import torch
        from transformers import (
            AutoModelForCausalLM,
            AutoTokenizer,
        )

        _configure_office_cuda_compatibility()

        if self.device == "cuda" and not torch.cuda.is_available():
            raise RuntimeError(
                "CUDA was requested for the local model but is unavailable."
            )

        self._tokenizer = AutoTokenizer.from_pretrained(
            self.model_name,
        )

        self._model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            dtype=torch.bfloat16,
            low_cpu_mem_usage=True,
            attn_implementation="sdpa",
        )

        self._model = self._model.to(
            self.device,
        )
        self._model.eval()

    def complete(
        self,
        system: str,
        user: str,
        temperature: float = 0.1,
        max_tokens: int = 1200,
    ) -> str:
        import torch

        self._load()

        assert self._tokenizer is not None
        assert self._model is not None

        messages = [
            {
                "role": "system",
                "content": system,
            },
            {
                "role": "user",
                "content": user,
            },
        ]

        try:
            prompt = self._tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
                enable_thinking=False,
            )
        except TypeError:
            prompt = self._tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )

        encoded = self._tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=self.max_context_tokens,
        )

        encoded = {
            key: value.to(self.device)
            for key, value in encoded.items()
        }

        generation_kwargs = {
            "max_new_tokens": max_tokens,
            "use_cache": True,
            "pad_token_id": self._tokenizer.eos_token_id,
        }

        if temperature > 0:
            generation_kwargs.update(
                {
                    "do_sample": True,
                    "temperature": temperature,
                }
            )
        else:
            generation_kwargs["do_sample"] = False

        with torch.inference_mode():
            output = self._model.generate(
                **encoded,
                **generation_kwargs,
            )

        generated = output[
            0,
            encoded["input_ids"].shape[1] :,
        ]

        return self._tokenizer.decode(
            generated,
            skip_special_tokens=True,
        ).strip()
