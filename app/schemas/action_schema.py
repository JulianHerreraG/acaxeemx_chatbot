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


class CancelarReserva(BaseModel):
    estado: bool = False
    nombre: Optional[str] = None
    telefono: Optional[str] = None
    fecha: Optional[str] = None
    hora: Optional[str] = None


class ConsultarDisponibilidad(BaseModel):
    estado: bool = False
    fecha: Optional[str] = None
    hora: Optional[str] = None


class MensajeRespuestaDirecto(BaseModel):
    estado: bool = False
    mensaje: Optional[str] = None


class ActionResponse(BaseModel):
    fecha_hora_actual: FechaHoraActual
    reserva: Reserva = Reserva()
    cancelar_reserva: CancelarReserva = CancelarReserva()
    consultar_disponibilidad: ConsultarDisponibilidad = ConsultarDisponibilidad()
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
            required = ["fecha", "hora"]
            for field in required:
                if getattr(self.consultar_disponibilidad, field) is None:
                    self.consultar_disponibilidad.estado = False
                    break

        return self
