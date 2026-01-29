from src.auth import AuthManager
from datetime import datetime, timedelta

def main():
    print("\n" + "="*50)
    print("      🔑 GENERADOR DE LLAVES DE ACCESO")
    print("="*50)
    print("\n┏━ SELECCIONA LA DURACIÓN DE LA LLAVE:\n")
    print("  1. ⏱️  24 horas (1 día)")
    print("  2. 📅 3 días")
    print("  3. 📅 10 días")
    print("  4. 📅 15 días")
    print("  5. 📆 1 mes (30 días)")
    print("  6. 📆 3 meses (90 días)")
    print("  7. 📆 6 meses (180 días)\n")
    print("┗" + "━"*48)
    
    # Duration options in hours
    duration_options = {
        '1': (24, '24 horas (1 día)'),
        '2': (72, '3 días'),
        '3': (240, '10 días'),
        '4': (360, '15 días'),
        '5': (720, '1 mes (30 días)'),
        '6': (2160, '3 meses (90 días)'),
        '7': (4320, '6 meses (180 días)')
    }
    
    # Get user input
    while True:
        try:
            choice = input("\n➤ Ingresa el número (1-7): ").strip()
            
            if choice in duration_options:
                duration_hours, duration_label = duration_options[choice]
                break
            else:
                print("❌ Opción inválida. Por favor ingresa un número del 1 al 7.")
        except KeyboardInterrupt:
            print("\n\n❌ Operación cancelada.")
            return
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # Generate key with selected duration
    auth = AuthManager()
    key = auth.generate_key(duration_hours=duration_hours)
    
    # Display result
    print("\n" + "="*50)
    print("     ✅ LLAVE GENERADA EXITOSAMENTE")
    print("="*50)
    print(f"\n🔑 Llave: {key}\n")
    print(f"⏱️  Duración: {duration_label}")
    
    if duration_hours is not None:
        expiration_date = datetime.now() + timedelta(hours=duration_hours)
        print(f"📅 Expira en: {expiration_date.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"\n⚠️  El tiempo empieza cuando el usuario CANJEE la llave.")
    else:
        print(f"♾️  Esta llave NO expira")
    
    print("\n" + "="*50)
    print("Comparte esta llave con el usuario.")
    print("Se usará una sola vez.")
    print("="*50 + "\n")

if __name__ == "__main__":
    main()

