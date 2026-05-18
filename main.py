import sys
import io

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from agent import Agent


def print_header():
    print("=" * 60)
    print(" AGENTE DE HOSPEDAGEM INTELIGENTE")
    print(" Farol Barra Flat | Ondina Apt Hotel | The Plaza | Smart Convencoes")
    print("=" * 60)
    print()


def print_help():
    print("Comandos disponiveis:")
    print("  /imoveis      - Listar todos os imoveis")
    print("  /stats        - Estatisticas de atendimento")
    print("  /novo         - Limpar conversa atual")
    print("  /ajuda        - Mostrar esta ajuda")
    print("  /sair         - Encerrar")
    print()


def list_properties(agent):
    print("NOSSOS IMOVEIS EM SALVADOR:\n")
    for key in agent.pm.list_properties():
        prop = agent.pm.get_property(key)
        print(prop.summary())
        print("  Diferenciais:")
        print(prop.amenities_text())
        print("-" * 50)
        print()


def main():
    agent = Agent()
    print_header()
    print_help()
    print(agent.templates.welcome_message())
    print()

    conversation_history = []

    while True:
        try:
            user_input = input("Voce: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nAtendimento encerrado. Obrigado!")
            break

        if not user_input:
            continue

        if user_input.lower() in ["/sair", "/exit", "/quit"]:
            print("\nAtendimento encerrado. Volte sempre!")
            break

        if user_input.lower() in ["/ajuda", "/help"]:
            print_help()
            continue

        if user_input.lower() in ["/imoveis", "/propriedades", "/lista"]:
            list_properties(agent)
            continue

        if user_input.lower() in ["/stats", "/estatisticas"]:
            stats = agent.get_stats()
            print(f"ESTATISTICAS:")
            print(f"  Total de clientes atendidos: {stats['total_guests']}")
            print(f"  Total de conversas: {stats['total_conversations']}")
            print(f"  Orcamentos enviados: {stats['quotes_sent']}")
            print(f"  Conversoes: {stats['conversions']}")
            continue

        if user_input.lower() in ["/novo", "/clear", "/reset"]:
            agent.current_guest = None
            agent.current_property = None
            conversation_history = []
            print("Conversa reiniciada. Como posso ajudar?")
            continue

        response = agent.respond(user_input)
        conversation_history.append((user_input, response))

        print(f"\nAgente:\n{response}\n")


if __name__ == "__main__":
    main()
