    if primary_signer.strip().lower() == payload.secondary_signer.strip().lower():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "dual-signature requirement: primary_signer and secondary_signer "
                "must be different people."
            ),
        )