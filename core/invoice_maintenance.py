"""Opaque, revocable invoice capabilities. Never stored in settings or SQLite."""
import weakref


class InvoiceMaintenance:
    _grants = {}

    @classmethod
    def issue(cls, owner, context):
        token = object()
        cls._grants[token] = (weakref.ref(owner, lambda _: cls.revoke(token)), context)
        return token

    @classmethod
    def valid(cls, token, context):
        try:
            grant = cls._grants.get(token)
        except TypeError:
            return False
        if not grant or grant[1] != context:
            return False
        owner = grant[0]()
        try:
            return owner is not None and (not hasattr(owner, "isVisible") or owner.isVisible())
        except RuntimeError:
            return False

    @classmethod
    def revoke(cls, token):
        try:
            grant = cls._grants.pop(token, None)
        except TypeError:
            return
        if grant:
            owner = grant[0]()
            callback = getattr(owner, "_maintenance_revoked", None)
            if callback:
                try:
                    callback(token)
                except RuntimeError:
                    pass

    @classmethod
    def revoke_all(cls):
        for token in list(cls._grants):
            cls.revoke(token)
