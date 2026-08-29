import secrets


def gerar_codigo_6_digitos():
    # Gera um número entre 100000 e 999999
    return str(secrets.randbelow(900000) + 100000)


if __name__ == "__main__":
    codigo = gerar_codigo_6_digitos()
    print(f"Código gerado: {codigo}")