import requests

menu_moedas = """

=== Opções de Moedas para Consulta ===

Tradicionais:

USD-BRL (Dólar Americano)
EUR-BRL (Euro)
GBP-BRL (Libra Esterlina)
ARS-BRL (Peso Argentino)

Criptomoedas:

BTC-BRL (Bitcoin)
ETH-BRL (Ethereum)

=====================================

"""

def consultar_moeda(moeda):
    url = f"https://economia.awesomeapi.com.br/json/last/{moeda}"
    resposta = requests.get(url)
    
    if resposta.status_code == 200:
        print("Deu certo!")
        dados = resposta.json()
        print(dados)
        return dados
    
    elif resposta.status_code == 404:
        erro=resposta.json()
        status=erro["status"]
        code=erro["code"]
        message=erro["message"]
        print(f"Erro {code}: {status}: {message}")


    else: print("Deu ruim!")

moeda_desejada = input("Digite a moeda que deseja consultar(ex: USD-BRL):")

dados_api = consultar_moeda(moeda_desejada)

if dados_api:
    chave = moeda_desejada.replace("-", "")
    valor = dados_api[chave]["bid"]
    print("\n=== Resultado da Consulta ===")
    print(f"Data da última atualização: {moeda_desejada} é: ")
    print(f"R$ {float(valor):.2f}")

else:
    print(f"\nErro ao consultar a moeda {moeda_desejada}. Verifique se a moeda está correta e tente novamente.")

