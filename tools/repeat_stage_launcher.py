"""Interactive local launcher; all execution belongs to the driver/Maa."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))


def main():
    print('Repetir fase pelo Try again (experimental; validacao ao vivo pendente).')
    print('Escolha a fase no jogo, termine uma batalha e deixe Try again visivel.')
    print('A quantidade abaixo conta NOVAS batalhas, alem dessa primeira.')
    print('Sem recarga automatica. Para parar: Ctrl+C ou crie var/STOP.')
    try:
        count = int(input('Quantas repeticoes (1 a 100)? '))
        budget = int(input('Limite total do recurso mostrado no botao? '))
        minutes = int(input('Prazo total em minutos (1 a 30)? '))
        if not 1 <= count <= 100 or budget <= 0 or not 1 <= minutes <= 30:
            raise ValueError('Limites invalidos.')
    except (ValueError, EOFError) as exc:
        print('Entrada invalida:', exc)
        return 1
    from driver_epic_seven.cli import main as driver_main
    return driver_main(['repeat-stage', '--count', str(count),
                        '--max-resource', str(budget), '--timeout', str(minutes * 60)])


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print('Interrompido. Confira o jogo antes de iniciar outro lote.')
        raise SystemExit(130)
