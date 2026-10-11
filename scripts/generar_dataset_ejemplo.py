#!/usr/bin/env python3
"""
Genera un dataset ejemplar de 200 pedidos de e-commerce (Temu, Shein,
AliExpress) para probar manualmente la plataforma de punta a punta:
subida de archivo, análisis automático, chat conversacional, gráficos,
dashboards, reportes, qué-pasa-si y recomendaciones proactivas.

No es un dataset "limpio" a propósito: incluye nulos, un par de outliers
de precio y una fila duplicada, para que el motor analítico (salud de
datos, anomalías, correlaciones, hallazgos) tenga algo real que detectar
— un CSV perfecto no demuestra nada de lo que el Módulo 3 hace.

Uso:
    python scripts/generar_dataset_ejemplo.py
    # o con otra ruta/tamaño:
    python scripts/generar_dataset_ejemplo.py --out mi_dataset.csv --filas 500
"""
import argparse
import csv
import random
from datetime import date, timedelta

PLATAFORMAS = ["Temu", "Shein", "AliExpress"]

CATEGORIAS = {
    "Temu": ["Hogar", "Electrónica", "Accesorios", "Jardín", "Juguetes"],
    "Shein": ["Ropa mujer", "Ropa hombre", "Calzado", "Accesorios", "Belleza"],
    "AliExpress": ["Electrónica", "Herramientas", "Hogar", "Accesorios móvil", "Deportes"],
}

PRODUCTOS = {
    "Hogar": ["Organizador de cocina", "Set de toallas", "Lámpara LED", "Set de cojines"],
    "Electrónica": ["Audífonos inalámbricos", "Cargador rápido 65W", "Mini parlante bluetooth", "Smartwatch"],
    "Accesorios": ["Mochila antirrobo", "Billetera RFID", "Gafas de sol", "Reloj digital"],
    "Jardín": ["Maceta autorregable", "Kit de riego por goteo", "Luces solares"],
    "Juguetes": ["Figura coleccionable", "Rompecabezas 1000 piezas", "Dron mini"],
    "Ropa mujer": ["Vestido floral", "Blusa oversize", "Jean mom fit", "Chaqueta denim"],
    "Ropa hombre": ["Camisa casual", "Jogger deportivo", "Chaqueta bomber"],
    "Calzado": ["Zapatillas urbanas", "Sandalias verano", "Botines"],
    "Belleza": ["Set de brochas", "Serum facial", "Plancha de cabello"],
    "Herramientas": ["Set de destornilladores", "Taladro inalámbrico", "Multímetro digital"],
    "Accesorios móvil": ["Funda protectora", "Vidrio templado", "Soporte para auto"],
    "Deportes": ["Banda de resistencia", "Botella térmica", "Guantes de gimnasio"],
}

PAISES_DESTINO = ["Colombia", "México", "Perú", "Chile", "Argentina", "Ecuador"]
METODOS_PAGO = ["Tarjeta de crédito", "Tarjeta débito", "PayPal", "Pago contraentrega"]
ESTADOS_PEDIDO = ["Entregado", "En tránsito", "Procesando", "Cancelado", "Devuelto"]


def generar_filas(n: int, seed: int = 42):
    random.seed(seed)
    filas = []
    hoy = date(2026, 10, 1)

    for i in range(1, n + 1):
        plataforma = random.choice(PLATAFORMAS)
        categoria = random.choice(CATEGORIAS[plataforma])
        producto = random.choice(PRODUCTOS[categoria])

        # Rangos de precio realistas por plataforma (Shein algo más caro
        # en promedio que Temu/AliExpress, con solapamiento real).
        precio_base = {"Temu": (3, 35), "Shein": (8, 60), "AliExpress": (5, 80)}[plataforma]
        precio = round(random.uniform(*precio_base), 2)

        cantidad = random.choices([1, 2, 3, 4, 5], weights=[55, 25, 10, 6, 4])[0]
        descuento_pct = random.choices([0, 10, 15, 20, 30, 50], weights=[30, 20, 20, 15, 10, 5])[0]
        envio = round(random.choice([0, 0, 1.99, 2.99, 4.99]), 2)
        calificacion = random.choices([5, 4, 3, 2, 1], weights=[40, 30, 15, 10, 5])[0]
        dias_entrega = random.randint(5, 35)
        fecha_pedido = hoy - timedelta(days=random.randint(0, 180))
        pais = random.choice(PAISES_DESTINO)
        metodo_pago = random.choice(METODOS_PAGO)
        estado = random.choices(ESTADOS_PEDIDO, weights=[60, 15, 10, 8, 7])[0]

        total = round(precio * cantidad * (1 - descuento_pct / 100) + envio, 2)

        filas.append(
            {
                "id_pedido": f"PED-{i:05d}",
                "fecha_pedido": fecha_pedido.isoformat(),
                "plataforma": plataforma,
                "categoria": categoria,
                "producto": producto,
                "precio_unitario": precio,
                "cantidad": cantidad,
                "descuento_pct": descuento_pct,
                "costo_envio": envio,
                "total_pedido": total,
                "metodo_pago": metodo_pago,
                "pais_destino": pais,
                "dias_entrega": dias_entrega,
                "calificacion_cliente": calificacion,
                "estado_pedido": estado,
            }
        )

    # --- Imperfecciones deliberadas, para que haya algo real que detectar ---

    # 1) Nulos en calificacion_cliente (pedidos sin reseña todavía) y en
    #    dias_entrega (pedidos aún en tránsito) — ~5% cada uno.
    for campo, pct in (("calificacion_cliente", 0.05), ("dias_entrega", 0.04)):
        for fila in random.sample(filas, k=max(1, int(n * pct))):
            fila[campo] = ""

    # 2) Dos outliers de precio/total claros (errores de carga típicos:
    #    un cero de más, o un pedido corporativo fuera de lo normal) para
    #    que Isolation Forest tenga algo inequívoco que marcar.
    for fila in random.sample(filas, k=2):
        fila["precio_unitario"] = round(fila["precio_unitario"] * 25, 2)
        fila["total_pedido"] = round(fila["precio_unitario"] * fila["cantidad"] + fila["costo_envio"], 2)

    # 3) Una fila duplicada exacta (error común de doble-click al exportar),
    #    para probar la deduplicación por hash y/o detección de duplicados.
    filas.append(dict(filas[10]))

    return filas


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="dataset_ejemplo_200_pedidos.csv")
    parser.add_argument("--filas", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    filas = generar_filas(args.filas, seed=args.seed)
    columnas = list(filas[0].keys())

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columnas)
        writer.writeheader()
        writer.writerows(filas)

    print(f"Dataset generado: {args.out} ({len(filas)} filas, {len(columnas)} columnas)")


if __name__ == "__main__":
    main()
