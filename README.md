# APP_REGISTROS_JUDICIALESYCEM

Sistema de gestión de pacientes Poder Judicial y CEM - Unidad de Seguros

## 🚀 Despliegue en Vercel

### Paso 1: Subir a GitHub

```bash
# Inicializar repo
git init

# Agregar todos los archivos
git add .

# Commit inicial
git commit -m "Dashboard V2 - Filtro, paginación, flujo completo"

# Crear repo en GitHub (sin README, sin .gitignore)
# Luego conectar:
git remote add origin https://github.com/TU_USUARIO/APP_REGISTROS_JUDICIALESYCEM.git
git branch -M main
git push -u origin main
```

### Paso 2: Conectar GitHub → Vercel

1. Ir a [vercel.com](https://vercel.com) → Sign Up (con GitHub)
2. Click **"Add New Project"**
3. Importar `APP_REGISTROS_JUDICIALESYCEM`
4. Framework Preset: **Other**
5. Click **Deploy**

### Paso 3: Configurar Variables de Entorno

En Vercel Dashboard → Project → Settings → Environment Variables:

| Variable | Valor |
|---|---|
| `SUPABASE_URL` | `https://lbqichqgufkpataypqqs.supabase.co` |
| `SUPABASE_ANON_KEY` | `eyJhbGciOiJIUzI1NiIs...` (tu Anon Key) |
| `SUPABASE_SERVICE_KEY` | `eyJhbGciOiJIUzI1NiIs...` (tu Service Role Key) |
| `SECRET_KEY` | `clave-secreta-app-pacientes-2026` |

⚠️ **IMPORTANTE:** La Service Role Key NUNCA debe estar en el frontend. Solo en variables de entorno del backend.

### Paso 4: Redeploy

Después de agregar las variables:
- Vercel Dashboard → Deployments → Click en los tres puntos → **Redeploy**

---

## 🗄️ Datos de Ejemplo (SQL para Supabase)

Ejecutar en Supabase → SQL Editor:

```sql
-- ============================================
-- DATOS DE EJEMPLO
-- ============================================

-- 1. Usuario admin
INSERT INTO pac_usuarios (nombres, apellidos, usuario, contraseña, rol, estado)
VALUES ('Admin', 'Sistema', 'admin', 'pbkdf2:sha256:...', 'administrador', 'activo');

-- 2. Pacientes de ejemplo
INSERT INTO pac_pacientes (tipo_documento, numero_documento, apellidos_nombres, hcl, fecha_nacimiento, origen, oficio, seguro, celular, direccion, distrito, peso, talla, pa, estado, created_at)
VALUES 
('DNI', '12345678', 'PEREZ GARCIA, JUAN CARLOS', 'HCL001', '1985-03-15', 'PODER JUDICIAL', 'OF-2026-001', 'SIS', '987654321', 'Av. Principal 123', 'Lima', 75.5, 1.70, '120/80', 'activo', NOW()),
('DNI', '87654321', 'GARCIA LOPEZ, MARIA ROSA', 'HCL002', '1990-07-22', 'CEM', 'CEM-2026-045', 'SIS', '987654322', 'Jr. Comercio 456', 'Callao', 62.0, 1.60, '110/70', 'activo', NOW()),
('DNI', '45678912', 'CASTILLO MAGALLANES, JUAN CARLOS', 'HCL003', '1978-11-05', 'PODER JUDICIAL', 'OF-2026-002', 'SIS', '987654323', 'Calle Los Pinos 789', 'San Isidro', 80.0, 1.75, '130/85', 'activo', NOW()),
('DNI', '78912345', 'GALLEGO ASCA, CARMEN ROSARIO', 'HCL004', '1982-01-30', 'CEM', 'CEM-2026-046', 'SIS', '987654324', 'Av. Javier Prado 100', 'Miraflores', 58.5, 1.55, '115/75', 'activo', NOW()),
('INDOCUMENTADO', NULL, 'SIN DOCUMENTO, PEDRO ANTONIO', NULL, '1995-09-10', 'PODER JUDICIAL', 'OF-2026-003', 'SIS', '987654325', 'Sin dirección', 'Desconocido', 70.0, 1.68, '125/82', 'activo', NOW());

-- 3. Citas programadas (PENDIENTE_VALIDACION)
INSERT INTO pac_citas_programadas (paciente_id, fecha_cita_sugerida, estado, created_at)
VALUES 
((SELECT id FROM pac_pacientes WHERE numero_documento = '45678912'), '2026-07-08', 'PENDIENTE_VALIDACION', NOW()),
((SELECT id FROM pac_pacientes WHERE numero_documento = '78912345'), '2026-07-08', 'PENDIENTE_VALIDACION', NOW()),
((SELECT id FROM pac_pacientes WHERE numero_documento = '12345678'), '2026-07-15', 'PENDIENTE_VALIDACION', NOW()),
((SELECT id FROM pac_pacientes WHERE numero_documento = '87654321'), '2026-07-20', 'PENDIENTE_VALIDACION', NOW());

-- 4. Citas validadas (VALIDADO)
INSERT INTO pac_citas_programadas (paciente_id, fecha_cita_sugerida, fecha_cita_confirmada, estado, fua_generado, created_at)
VALUES 
((SELECT id FROM pac_pacientes WHERE numero_documento = '12345678'), '2026-07-09', '2026-07-09', 'VALIDADO', true, NOW()),
((SELECT id FROM pac_pacientes WHERE numero_documento = '87654321'), '2026-07-10', '2026-07-10', 'VALIDADO', false, NOW()),
((SELECT id FROM pac_pacientes WHERE tipo_documento = 'INDOCUMENTADO'), '2026-07-12', '2026-07-12', 'VALIDADO', false, NOW());

-- 5. Validaciones SIS
INSERT INTO pac_validaciones_sis (paciente_id, cita_programada_id, fecha_validacion, sis_estado, observacion, validado_por, semana_anio, anio)
VALUES 
((SELECT id FROM pac_pacientes WHERE numero_documento = '12345678'), (SELECT id FROM pac_citas_programadas WHERE fecha_cita_confirmada = '2026-07-09'), '2026-07-07', 'ACTIVO', 'SIS activo, sin observaciones', (SELECT id FROM pac_usuarios WHERE usuario = 'admin'), 28, 2026),
((SELECT id FROM pac_pacientes WHERE numero_documento = '87654321'), (SELECT id FROM pac_citas_programadas WHERE fecha_cita_confirmada = '2026-07-10'), '2026-07-07', 'ACTIVO', 'Verificado en web SIS', (SELECT id FROM pac_usuarios WHERE usuario = 'admin'), 28, 2026);

-- 6. Atenciones
INSERT INTO pac_atenciones (paciente_id, fecha_atencion, mes, anio, motivo, diagnostico, tratamiento, pa, fc, fr, temperatura, peso, talla, imc, observaciones, proxima_cita, registrado_por)
VALUES 
((SELECT id FROM pac_pacientes WHERE numero_documento = '12345678'), '2026-07-01', 7, 2026, 'Control mensual', 'Z00.0 - Examen médico general', 'Continuar tratamiento', '120/80', 72, 18, 36.5, 75.5, 1.70, 26.1, 'Paciente estable', '2026-07-09', (SELECT id FROM pac_usuarios WHERE usuario = 'admin')),
((SELECT id FROM pac_pacientes WHERE numero_documento = '87654321'), '2026-07-02', 7, 2026, 'Dolor abdominal', 'R10.4 - Dolor abdominal', 'Paracetamol 500mg', '110/70', 68, 16, 37.2, 62.0, 1.60, 24.2, 'Mejoría', '2026-07-10', (SELECT id FROM pac_usuarios WHERE usuario = 'admin'));
```

---

## 📁 Estructura del Proyecto

```
APP_REGISTROS_JUDICIALESYCEM/
├── api/
│   └── index.py              # Backend Flask (Vercel Serverless)
├── static/
│   └── img/
│       ├── image.png         # Logo principal
│       └── suladmental.png   # Logo SULAD Mental
├── templates/
│   ├── login.html            # Login
│   ├── dashboard.html        # Dashboard V2 (filtro + paginación)
│   └── ficha_paciente.html   # Ficha del paciente
├── .env.example              # Ejemplo de variables (NO subir)
├── .gitignore                # Ignorar .env, __pycache__
├── requirements.txt          # Dependencias Python
├── vercel.json               # Configuración Vercel
└── README.md                 # Este archivo
```

---

## 🔧 Tecnologías

- **Backend:** Flask 3.0 + Python 3.9+
- **Base de datos:** Supabase (PostgreSQL)
- **Frontend:** HTML5 + CSS3 + Vanilla JS
- **Gráficos:** Chart.js 4.4
- **Exportar:** SheetJS + jsPDF
- **Hosting:** Vercel (Serverless)

---

## ⚠️ Notas Importantes

1. **Service Role Key:** NUNCA exponer en el frontend. Solo usar en backend (`api/index.py`).
2. **RLS:** Las tablas tienen Row Level Security. El backend usa Service Role para escrituras.
3. **Session:** Flask sessions funcionan en Vercel con `SECRET_KEY` configurada.
4. **Imágenes:** Subir `image.png` y `suladmental.png` a `static/img/`.

---

## 🔄 Flujo V2

```
Triaje → Registrar Paciente → Registrar Atención → Próxima Cita
                                                            ↓
                                            Cita PENDIENTE_VALIDACION
                                                            ↓
                                            Validar SIS → VALIDADO
                                                            ↓
                                            Programación Anual (Admisión)
                                                            ↓
                                            Confirmar fecha + FUA
                                                            ↓
                                            Pendientes por Atender (hoy+7 días)
                                                            ↓
                                            Nueva Atención → (ciclo)
```

---

Desarrollado para Unidad de Seguros - Atenciones Poder Judicial y CEM
