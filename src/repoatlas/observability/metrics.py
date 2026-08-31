def gpu_memory_snapshot():
    try:
        import torch

        if torch.cuda.is_available():
            return {
                "allocated_gb": torch.cuda.memory_allocated() / 1e9,
                "reserved_gb": torch.cuda.memory_reserved() / 1e9,
                "device": torch.cuda.get_device_name(0),
            }

        return {"device": "cpu"}

    except (ImportError, RuntimeError) as exc:
        return {
            "device": "unavailable",
            "error": str(exc),
        }
