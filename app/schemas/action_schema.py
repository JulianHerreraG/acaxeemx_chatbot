from typing import Optional
from pydantic import BaseModel, model_validator


class FechaHoraActual(BaseModel):
    Hora: str
    fecha: str


class Reserva(BaseModel):
    estado: bool = False
    nombre: Optional[str] = None
    numero_personas: Optional[int] = None
    telefono: Optional[str] = None
    fecha: Optional[str] = None
    hora: Optional[str] = None
    mensaje_si_exitoso: Optional[str] = None
    occasion_signals: list[str] = []


class CancelarReserva(BaseModel):
    estado: bool = False
    nombre: Optional[str] = None
    telefono: Optional[str] = None
    fecha: Optional[str] = None
    hora: Optional[str] = None
    mensaje_si_exitoso: Optional[str] = None


class ConsultarDisponibilidad(BaseModel):
    estado: bool = False
    fecha: Optional[str] = None
    hora: Optional[str] = None
    numero_personas: Optional[int] = None


class ConsultarReserva(BaseModel):
    estado: bool = False
    nombre: Optional[str] = None
    telefono: Optional[str] = None


class ModificarReserva(BaseModel):
    estado: bool = False
    # Datos de la reserva original a cancelar
    nombre_original: Optional[str] = None
    telefono_original: Optional[str] = None
    fecha_original: Optional[str] = None
    hora_original: Optional[str] = None
    # Datos de la nueva reserva
    nombre_nuevo: Optional[str] = None
    numero_personas_nuevo: Optional[int] = None
    telefono_nuevo: Optional[str] = None
    fecha_nueva: Optional[str] = None
    hora_nueva: Optional[str] = None
    mensaje_si_exitoso: Optional[str] = None


class SolicitarAsistenciaAdmin(BaseModel):
    estado: bool = False
    motivo: Optional[str] = None
    mensaje_para_usuario: Optional[str] = None


class MensajeRespuestaDirecto(BaseModel):
    estado: bool = False
    mensaje: Optional[str] = None


class ActionResponse(BaseModel):
    fecha_hora_actual: FechaHoraActual
    reserva: Reserva = Reserva()
    cancelar_reserva: CancelarReserva = CancelarReserva()
    consultar_disponibilidad: ConsultarDisponibilidad = ConsultarDisponibilidad()
    consultar_reserva: ConsultarReserva = ConsultarReserva()
    modificar_reserva: ModificarReserva = ModificarReserva()
    solicitar_asistencia_admin: SolicitarAsistenciaAdmin = SolicitarAsistenciaAdmin()
    mensaje_respuesta_directo: MensajeRespuestaDirecto = MensajeRespuestaDirecto()

    @model_validator(mode="after")
    def validate_action_fields(self):
        if self.reserva.estado:
            required = ["nombre", "numero_personas", "telefono", "fecha", "hora"]
            for field in required:
                if getattr(self.reserva, field) is None:
                    self.reserva.estado = False
                    break

        if self.cancelar_reserva.estado:
            required = ["nombre", "telefono", "fecha", "hora"]
            for field in required:
                if getattr(self.cancelar_reserva, field) is None:
                    self.cancelar_reserva.estado = False
                    break

        if self.consultar_disponibilidad.estado:
            # Solo fecha es requerida; hora y numero_personas son opcionales
            if not self.consultar_disponibilidad.fecha:
                self.consultar_disponibilidad.estado = False

        # modificar_reserva se activa con nombre_original + telefono_original
        if self.modificar_reserva.estado:
            if not self.modificar_reserva.nombre_original or not self.modificar_reserva.telefono_original:
                self.modificar_reserva.estado = False

        if self.consultar_reserva.estado:
            if not self.consultar_reserva.nombre or not self.consultar_reserva.telefono:
                self.consultar_reserva.estado = False

        return self
