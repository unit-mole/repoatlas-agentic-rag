class DisabledCommercialProvider:
    def complete(self, *args, **kwargs):
        raise RuntimeError(
            "Commercial providers are disabled by default. Set ENABLE_COMMERCIAL_MODELS=true and configure an adapter explicitly."
        )
