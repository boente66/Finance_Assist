"""Backups e alertas periódicos enquanto o Finance Assist está aberto."""

from datetime import datetime, timedelta
import logging
import os
from pathlib import Path
import secrets
import sqlite3
import threading

from PyQt5.QtCore import QObject, QTimer, pyqtSignal

from core.config import DATA_DIR, carregar_config, get_db_path, salvar_config
from core.session import Session
from models.backup_model import BackupModel

logger = logging.getLogger(__name__)


class BackgroundManager(QObject):
    notification = pyqtSignal(str, str)
    backup_finished = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._backup_running = False
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_now)
        self.timer.start(60_000)
        self.initial_timer = QTimer(self)
        self.initial_timer.setSingleShot(True)
        self.initial_timer.timeout.connect(self.check_now)
        self.initial_timer.start(3_000)

    def check_now(self):
        config = carregar_config()
        usuario = Session.get_usuario() or {}
        if config.get("notificacoes_ativas", True):
            self._check_alerts(usuario, config)
        if (
            config.get("backup_automatico", False)
            and str(usuario.get("Nivel_Acesso", "")).lower() == "admin"
            and self._backup_due(config)
            and not self._backup_running
        ):
            self._backup_running = True
            threading.Thread(target=self._create_backup, daemon=True).start()

    @staticmethod
    def _backup_due(config):
        try:
            last = datetime.fromisoformat(config.get("ultimo_backup_automatico", ""))
        except (TypeError, ValueError):
            return True
        return datetime.now() - last >= timedelta(hours=max(1, int(config.get("backup_intervalo_horas", 24))))

    @staticmethod
    def _device_secret():
        path = Path(DATA_DIR) / ".automatic_backup_key"
        if not path.exists():
            path.write_text(secrets.token_urlsafe(48), encoding="utf-8")
            try:
                path.chmod(0o600)
            except OSError:
                pass
        return path.read_text(encoding="utf-8").strip()

    def _create_backup(self):
        try:
            directory = Path(DATA_DIR) / "backups" / "automaticos"
            directory.mkdir(parents=True, exist_ok=True)
            path = BackupModel(get_db_path()).criar_backup(
                str(directory), self._device_secret(), prefixo="backup_automatico"
            )
            config = carregar_config()
            config["ultimo_backup_automatico"] = datetime.now().isoformat()
            salvar_config(config)
            files = sorted(directory.glob("backup_automatico_*.kp"), key=lambda p: p.stat().st_mtime, reverse=True)
            for old in files[max(1, int(config.get("backup_retencao", 7))):]:
                old.unlink(missing_ok=True)
            self.backup_finished.emit(path)
        except Exception:
            logger.exception("Falha no backup automático")
            self.notification.emit("Backup automático", "Não foi possível criar o backup automático. Consulte o log.")
        finally:
            self._backup_running = False

    def _check_alerts(self, usuario, config):
        user_id = usuario.get("ID_Usuario")
        if not user_id:
            return
        intervalo = max(5, int(config.get("alerta_intervalo_minutos", 30)))
        key = f"ultimo_alerta_usuario_{user_id}"
        try:
            last = datetime.fromisoformat(config.get(key, ""))
            if datetime.now() - last < timedelta(minutes=intervalo):
                return
        except (TypeError, ValueError):
            pass
        try:
            with sqlite3.connect(get_db_path()) as conn:
                overdue = conn.execute(
                    """SELECT COUNT(*) FROM agendamentos WHERE ID_Usuario=? AND Ativo=1
                       AND Status IN ('AGENDADO','ATRASADO') AND date(Data)<date('now')""",
                    (user_id,),
                ).fetchone()[0]
            if overdue:
                self.notification.emit("Finance Assist", f"Você possui {overdue} agendamento(s) vencido(s).")
            config[key] = datetime.now().isoformat()
            salvar_config(config)
        except Exception:
            logger.exception("Falha ao consultar alertas")
