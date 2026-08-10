"""Advanced interoperability lab: capability and identity checks at a boundary."""


def accept_request(identity: str, capability: str, requested: str) -> dict:
    allowed = {"research-agent": {"search", "summarize"}, "billing-agent": {"lookup"}}
    if requested not in allowed.get(identity, set()):
        return {"accepted": False, "reason": "capability not granted"}
    if capability != requested:
        return {"accepted": False, "reason": "declared capability does not match request"}
    return {"accepted": True, "identity": identity, "capability": requested}


if __name__ == "__main__":
    print(accept_request("research-agent", "search", "search"))
    print(accept_request("research-agent", "charge", "charge"))
