from src.auth import AuthManager

def main():
    auth = AuthManager()
    key = auth.generate_key()
    print("\n" + "="*30)
    print("🔑 NUEVA LLAVE DE ACCESO GENERADA")
    print("="*30)
    print(f"\n   {key}\n")
    print("="*30)
    print("Comparte esta llave con el usuario.")
    print("Se usará una sola vez.")

if __name__ == "__main__":
    main()
