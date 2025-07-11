INSERT INTO ventas (tipo, color, material, agregado, cantidad, precioU, precioT, fecha)
VALUES 
('Silla giratoria', 'Rojo', 'Metal', 'Con brazos', 2, 150.00, 300.00, '2024-06-30'),
('Catre de internación', 'Rojo', 'Metal', 'Con barillas', 1, 2650.00, 2650.00, '2024-06-30'),
('Camilla tipo escritorio', 'Gris', 'Metal', 'Con espaldar movible', 3, 2750.00, 8250.00, '2024-06-30'),
('Taburete médico', 'Blanco', 'Metal', 'Con ruedas', 2, 630.00, 1260.00, '2024-06-30'),
('Mesa de trabajo', 'Negro', 'Metal', 'Sin cajones', 4, 1200.00, 4800.00, '2024-06-30'),
('Vitrina para farmacia', 'Blanco', 'Melamina', 'Con iluminación', 1, 1800.00, 1800.00, '2024-06-30'),
('Estante para farmacia de dos cuerpos', 'Blanco', 'Melamina', 'De pie', 2, 750.00, 1500.00, '2024-06-30'),
('Gabinete de dos cuerpos', 'Blanco', 'Melamina', 'Con espejo', 1, 1100.00, 1100.00, '2024-06-30'),
('Gradilla de 2 peldaños', 'Negro', 'Metal', 'Sin agregado', 3, 450.00, 1350.00, '2024-06-30'),
('Biombo', 'Azul', 'Melamina', 'Sin agregado', 1, 450.00, 450.00, '2024-06-30'),
('Lámpara de cuello ganzo', 'Blanco', 'Metal', 'Sin agregado', 2, 320.00, 640.00, '2024-06-30'),
('Casillero de 6 puertas', 'Gris', 'Metal', 'Sin agregado', 1, 1250.00, 1250.00, '2024-06-30'),
('Estanteria tipo vitrin', 'Rojo', 'Metal', 'Sin agregado', 2, 850.00, 1700.00, '2024-06-30'),
('Escritorio secretarial de cuatro cajas con chapa clave', 'Negro', 'Melamina', 'Con ruedas', 1, 1650.00, 1650.00, '2024-06-30'),
('Silla estática', 'Azul', 'Metal', 'Sin brazos', 4, 180.00, 720.00, '2024-06-30');

INSERT INTO usuario (ROL, TIPO) VALUES
(1001, 'Administrador'),
(1002, 'Encargado'),
(1003, 'Empleado');

INSERT INTO persona (nombre, apellido, ci, genero, email, telefono, direccion, fecha_nacimiento, rol) VALUES
('Juan', 'Pérez', 12345678, 'M', 'juan.perez@example.com', '555-1234', 'Calle Falsa 123, Ciudad', '1985-01-15', 1001),
('María', 'González', 23456789, 'F', 'maria.gonzalez@example.com', '555-5678', 'Avenida Siempre Viva 456, Ciudad', '1990-03-22', 1002),
('Carlos', 'Rodríguez', 34567890, 'M', 'carlos.rodriguez@example.com', '555-9012', 'Boulevard del Sol 789, Ciudad', '1987-07-10', 1002),
('Ana', 'López', 45678901, 'F', 'ana.lopez@example.com', '555-3456', 'Plaza Central 101, Ciudad', '1992-12-05', 1002),
('Luis', 'Martínez', 56789012, 'M', 'luis.martinez@example.com', '555-7890', 'Calle Larga 202, Ciudad', '1983-04-18', 1003),
('Sofía', 'Hernández', 67890123, 'F', 'sofia.hernandez@example.com', '555-2345', 'Avenida del Parque 303, Ciudad', '1995-09-30', 1003),
('Miguel', 'García', 78901234, 'M', 'miguel.garcia@example.com', '555-6789', 'Calle de la Luna 404, Ciudad', '1989-06-15', 1003),
('Laura', 'Ramírez', 89012345, 'F', 'laura.ramirez@example.com', '555-0123', 'Paseo del Río 505, Ciudad', '1993-11-25', 1003),
('David', 'Fernández', 90123456, 'M', 'david.fernandez@example.com', '555-4567', 'Calle de las Flores 606, Ciudad', '1986-08-05', 1003),
('Carmen', 'Sánchez', 11234567, 'F', 'carmen.sanchez@example.com', '555-8901', 'Avenida del Mar 707, Ciudad', '1991-02-20', 1003);

SELECT 
    p.id AS persona_id, 
    p.nombre AS nombre, 
    p.apellido AS apellido, 
    p.ci AS ci, 
    p.genero AS genero, 
    p.email AS email, 
    p.telefono AS telefono, 
    p.direccion AS direccion, 
    p.fecha_nacimiento AS fecha_nacimiento, 
    u.TIPO AS rol 
FROM 
    persona AS p
JOIN 
    usuario AS u ON p.rol = u.ROL
WHERE 
    u.TIPO = 'encargado';

INSERT INTO stock (tipo, color, material, agregado, cantidad) VALUES
('Silla giratoria', 'Rojo', 'Metal', 'Con brazos', 35),
('Silla de espera', 'Azul', 'Melamina', 'Sin brazos', 40),
('Silla estática', 'Negro', 'Metal', 'Acolchonada', 45),
('Silla mesedora', 'Blanco', 'Melamina', 'No acolchonada', 32),
('Silla de peluquería', 'Gris', 'Metal', 'Con brazos', 37),
('Silla estática con brazo', 'Rojo', 'Melamina', 'Acolchonada', 38),
('Catre de internación', 'Blanco', 'Metal', 'Con cabecera', 39),
('Camillas para masajes', 'Negro', 'Metal', 'Con espaldar movible', 41),
('Gradilla de 2 peldaños', 'Gris', 'Metal', '', 42),
('Biombo', 'Blanco', 'Metal', '', 43),
('Negtoscopio', 'Negro', 'Melamina', '', 36),
('Camilla tipo escritorio', 'Gris', 'Melamina', 'Fija', 35),
('Taburete médico', 'Negro', 'Metal', '', 34),
('Camilla con Barillas', 'Blanco', 'Metal', 'Con barillas', 40),
('Lámpara de cuello ganzo', 'Gris', 'Metal', '', 37),
('Velador clínico', 'Negro', 'Melamina', '', 38),
('Camilla de ginecología', 'Blanco', 'Metal', '', 39),
('Pedestal porta sueros', 'Gris', 'Metal', '', 36),
('Camilla de examen', 'Negro', 'Metal', '', 41),
('Camilla de examen con espaldar movible', 'Blanco', 'Metal', 'Con espaldar movible', 35),
('Mesa de trabajo', 'Gris', 'Melamina', 'Cuadrada', 34),
('Mesa de curación', 'Negro', 'Metal', 'Redonda', 36),
('Mesa de instrumentación', 'Blanco', 'Melamina', 'Con cajones', 37),
('Horno semi-industrial', 'Gris', 'Metal', 'A gas', 35),
('Cocina industrial de dos quemadores', 'Negro', 'Melamina', 'A gas', 38),
('Horno domestico', 'Blanco', 'Metal', 'Eléctrico', 40),
('Broastera simple', 'Gris', 'Melamina', 'A gas', 33),
('Horno hogareño', 'Negro', 'Metal', 'Con ventilador', 35),
('Góndolas para supermercados', 'Blanco', 'Melamina', '', 42),
('Estanteria tipo vitrin', 'Gris', 'Metal', 'Con puertas', 39),
('Casillero de cuatro puertas', 'Rojo', 'Metal', 'Con chapa', 37),
('Estante de puertas corredizas', 'Azul', 'Melamina', 'De pie', 38),
('Casillero de dos puertas', 'Negro', 'Metal', 'Con chapa', 36),
('Casillero de 6 puertas', 'Blanco', 'Melamina', 'Sin chapa', 39),
('Casillero de 12 puertas', 'Gris', 'Metal', 'Con espejo', 40),
('Casillero de 15 puertas', 'Rojo', 'Melamina', 'Sin espejo', 35),
('Casillero de 2 puertas', 'Azul', 'Metal', 'Con chapa', 37),
('Casillero de 20 puertas', 'Negro', 'Melamina', 'Con espejo', 38),
('Casillero de 9 puertas', 'Blanco', 'Metal', 'Sin chapa', 36),
('Casillero de 1 cuerpo y 4 puertas', 'Gris', 'Melamina', 'Con espejo', 37),
('Casillero de 1 cuerpo y tres puertas', 'Rojo', 'Metal', 'Sin chapa', 38),
('Casillero de 1 cuerpo y 1 puerta', 'Azul', 'Melamina', 'Con chapa', 35),
('Vitrina doble chapa', 'Negro', 'Metal', 'De vidrio', 36),
('Ropero casillero', 'Blanco', 'Melamina', 'Sin espejo', 39),
('Alacena con pedestal', 'Gris', 'Metal', '', 40),
('Cajero para supermercado', 'Rojo', 'Melamina', '', 34),
('Mostrador para librería', 'Azul', 'Metal', '', 38),
('Estante mostrador', 'Negro', 'Melamina', '', 39),
('Credenza', 'Blanco', 'Metal', '', 37),
('Estante Archivador', 'Gris', 'Melamina', 'De pared', 36),
('Estante para farmacia de dos cuerpos', 'Rojo', 'Metal', '', 35),
('Estante para farmacia', 'Azul', 'Melamina', 'Con puertas', 38),
('Vitrina para farmacia', 'Negro', 'Metal', 'De vidrio', 40),
('Estante para farmacia', 'Blanco', 'Melamina', 'De pie', 37),
('Escritorio secretarial de cuatro cajas con chapa clave', 'Gris', 'Metal', 'Con chapas', 35),
('Escritorio ejecutivo de siete cajas', 'Rojo', 'Melamina', 'Sin chapas', 34),
('Vitrina de puertas corredizas', 'Azul', 'Metal', 'De vidrio', 36),
('Gabinete de dos cuerpos', 'Negro', 'Melamina', 'Sin iluminación', 38),
('Armario de dos cuerpos', 'Blanco', 'Metal', 'Metálico', 40),
('Estante para archivos con bandejas', 'Gris', 'Melamina', '', 39),
('Archivero', 'Rojo', 'Metal', 'De oficina', 36),
('Gabetero con chapa independiente', 'Azul', 'Melamina', 'Con cerradura', 35),
('Archivador de Chapas Individuales', 'Negro', 'Metal', '', 38),
('Gabetero de 4 cajas', 'Blanco', 'Melamina', 'De hogar', 37),
('Gabetero de 3 cajas', 'Gris', 'Metal', 'Sin cerradura', 36),
('Gabetero de 2 cajas con chapa adicional', 'Rojo', 'Melamina', 'De oficina', 35),
('Gabetero de 2 cajas sin chapa', 'Azul', 'Metal', 'Sin cerradura', 38),
('Gabetero de 5 cajas', 'Negro', 'Melamina', 'Con cerradura', 40);


