def require_api_key(result, generator, request, public):
    """Make the OpenAPI security contract match the API-key middleware."""
    for path, path_item in result.get("paths", {}).items():
        if not path.startswith("/api/") or path == "/api/schema/":
            continue
        for operation in path_item.values():
            if not isinstance(operation, dict) or "responses" not in operation:
                continue
            existing = operation.get("security", [])
            needs_jwt = any("jwtAuth" in requirement for requirement in existing)
            requirement = {"ApiKeyAuth": []}
            if needs_jwt:
                requirement["jwtAuth"] = []
            operation["security"] = [requirement]
    return result
