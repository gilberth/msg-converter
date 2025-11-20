#!/usr/bin/env python3
"""
Ejemplo de uso del convertidor MSG a EML

Este script demuestra diferentes formas de usar el convertidor.
"""

from msg_to_eml_converter import MSGToEMLConverter
import os


def ejemplo_basico():
    """Ejemplo de conversión básica de un archivo"""
    print("=" * 60)
    print("EJEMPLO 1: Conversión básica de un archivo")
    print("=" * 60)

    converter = MSGToEMLConverter()

    # Simular conversión (necesitarías un archivo .msg real)
    msg_file = 'ejemplo.msg'

    if os.path.exists(msg_file):
        try:
            eml_file = converter.convert_file(msg_file, verbose=True)
            print(f"\n✓ Archivo convertido exitosamente: {eml_file}")
        except Exception as e:
            print(f"\n✗ Error: {e}")
    else:
        print(f"\nNota: Para probar este ejemplo, coloca un archivo '{msg_file}' en este directorio")
    print()


def ejemplo_con_salida_personalizada():
    """Ejemplo de conversión con nombre de archivo de salida personalizado"""
    print("=" * 60)
    print("EJEMPLO 2: Conversión con salida personalizada")
    print("=" * 60)

    converter = MSGToEMLConverter()

    msg_file = 'mensaje_importante.msg'
    eml_file = 'convertido/mensaje_importante_backup.eml'

    if os.path.exists(msg_file):
        # Crear directorio de salida si no existe
        os.makedirs('convertido', exist_ok=True)

        try:
            resultado = converter.convert_file(msg_file, eml_file, verbose=True)
            print(f"\n✓ Archivo guardado en: {resultado}")
        except Exception as e:
            print(f"\n✗ Error: {e}")
    else:
        print(f"\nNota: Para probar este ejemplo, coloca un archivo '{msg_file}' en este directorio")
    print()


def ejemplo_directorio():
    """Ejemplo de conversión de todos los archivos en un directorio"""
    print("=" * 60)
    print("EJEMPLO 3: Conversión por lotes de un directorio")
    print("=" * 60)

    converter = MSGToEMLConverter()

    input_dir = 'mensajes_entrada'
    output_dir = 'mensajes_convertidos'

    if os.path.exists(input_dir):
        try:
            archivos = converter.convert_directory(
                input_dir=input_dir,
                output_dir=output_dir,
                verbose=True
            )
            print(f"\n✓ Se convirtieron {len(archivos)} archivos")
            print("Archivos creados:")
            for archivo in archivos:
                print(f"  - {archivo}")
        except Exception as e:
            print(f"\n✗ Error: {e}")
    else:
        print(f"\nNota: Para probar este ejemplo, crea un directorio '{input_dir}' con archivos .msg")
    print()


def ejemplo_manejo_errores():
    """Ejemplo de manejo de errores durante la conversión"""
    print("=" * 60)
    print("EJEMPLO 4: Manejo de errores")
    print("=" * 60)

    converter = MSGToEMLConverter()

    archivos_a_convertir = [
        'email1.msg',
        'email2.msg',
        'email3.msg'
    ]

    convertidos = []
    errores = []

    for msg_file in archivos_a_convertir:
        try:
            if os.path.exists(msg_file):
                eml_file = converter.convert_file(msg_file)
                convertidos.append(eml_file)
                print(f"✓ {msg_file} -> {eml_file}")
            else:
                errores.append((msg_file, "Archivo no encontrado"))
                print(f"✗ {msg_file}: Archivo no encontrado")
        except Exception as e:
            errores.append((msg_file, str(e)))
            print(f"✗ {msg_file}: {e}")

    print(f"\nResumen:")
    print(f"  Convertidos: {len(convertidos)}")
    print(f"  Errores: {len(errores)}")
    print()


def ejemplo_uso_como_modulo():
    """Ejemplo de cómo usar el convertidor como módulo en tu propio código"""
    print("=" * 60)
    print("EJEMPLO 5: Uso como módulo")
    print("=" * 60)

    print("""
# En tu propio script Python:

from msg_to_eml_converter import MSGToEMLConverter

def procesar_emails_del_proyecto():
    converter = MSGToEMLConverter()

    # Convertir archivo específico
    converter.convert_file(
        msg_path='datos/email.msg',
        eml_path='salida/email.eml',
        verbose=True
    )

    # O procesar directorio completo
    archivos = converter.convert_directory(
        input_dir='datos/emails_msg',
        output_dir='salida/emails_eml',
        verbose=False
    )

    return archivos

# Llamar la función
archivos_convertidos = procesar_emails_del_proyecto()
print(f"Se procesaron {len(archivos_convertidos)} emails")
    """)
    print()


def main():
    """Ejecutar todos los ejemplos"""
    print("\n")
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 10 + "EJEMPLOS DE USO: MSG TO EML CONVERTER" + " " * 11 + "║")
    print("╚" + "═" * 58 + "╝")
    print()

    # Ejecutar ejemplos
    ejemplo_basico()
    ejemplo_con_salida_personalizada()
    ejemplo_directorio()
    ejemplo_manejo_errores()
    ejemplo_uso_como_modulo()

    print("=" * 60)
    print("Para más información, consulta el README.md")
    print("=" * 60)
    print()


if __name__ == '__main__':
    main()
