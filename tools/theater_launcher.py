"""Interactive Theater launcher. Game flow is executed by the driver's Maa graph."""
from pathlib import Path
import argparse
import ctypes
import os
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT/'tools'))


def main():
    parser=argparse.ArgumentParser(description='Moonlight Theater: Watch e avancar historias')
    parser.add_argument('--acts',type=int)
    parser.add_argument('--max-tickets',type=int)
    parser.add_argument('--minutes',type=int)
    parser.add_argument('--finish-current',action='store_true',help='Concluir um ato pendente sem novo ingresso')
    parser.add_argument('--elevated',action='store_true',help=argparse.SUPPRESS)
    options=parser.parse_args()
    os.chdir(ROOT)
    if os.name!='nt':
        print('Este lancador requer Windows.')
        return 1
    if not ctypes.windll.shell32.IsUserAnAdmin():
        if options.elevated:
            print('Nao foi possivel obter permissao de administrador.')
            return 1
        arguments=subprocess.list2cmdline([str(Path(__file__).resolve()),*sys.argv[1:],'--elevated'])
        result=ctypes.windll.shell32.ShellExecuteW(None,'runas',sys.executable,arguments,str(ROOT),1)
        if result<=32:
            print('O Windows nao autorizou abrir o driver como administrador.')
            return 1
        return 10
    from driver_epic_seven.config import load_config
    import json
    ledger_path=load_config()['path_ledger']
    ledger=json.loads(ledger_path.read_text(encoding='utf-8')) if ledger_path.exists() else {'stages':{}}
    pending=[key for key,rows in ledger['stages'].items() if key.startswith('theater:') and rows and rows[-1]['status']!='verified']
    finish_current=options.finish_current or bool(pending)
    print('Moonlight Theater - Watch e avancar historias')
    print('Deixe o Theater aberto no ato que deseja assistir, com Watch disponivel.')
    print('Um ingresso por ato; sem compras ou coleta de recompensas.')
    print('O jogo seleciona o proximo ato ao concluir. Para parar: Ctrl+C ou var/STOP.')
    print('Auto so e acionado quando o HUD comprova desligado; variante do Theater ainda em calibracao.')
    try:
        if finish_current:
            print('Ha um ato pendente: vou continuar somente esse ato, sem Watch/Confirm ou novo ingresso.')
            acts,tickets=1,0
        else:
            acts=options.acts if options.acts is not None else int(input('Quantos atos (1 a 20)? '))
            tickets=options.max_tickets if options.max_tickets is not None else int(input('Maximo de ingressos para usar? '))
        minutes=options.minutes if options.minutes is not None else int(input('Prazo total em minutos (1 a 30)? '))
        if not 1<=acts<=20 or not (tickets==0 if finish_current else acts<=tickets<=100) or not 1<=minutes<=30:
            raise ValueError('Limites invalidos: um ingresso por ato e prazo de ate 30 minutos.')
    except (ValueError,EOFError) as exc:
        print('Entrada invalida:',exc)
        return 1
    from driver_epic_seven.cli import parser as driver_parser,execute
    from theater_terminal import TerminalMonitor,prepare_session
    try:
        argv=['theater','--acts',str(acts),'--max-tickets',str(tickets),'--timeout',str(minutes*60)]
        if finish_current:argv.append('--finish-current')
        report_root,report_config=prepare_session(load_config())
        args=driver_parser().parse_args(['--config',str(report_config),*argv])
        print('Registro do acompanhamento:',report_root/'progresso.log',flush=True)
        with TerminalMonitor(report_root,acts,minutes*60) as monitor:
            result=execute(args)
            monitor.complete(result)
    except (RuntimeError,ValueError,OSError,ImportError) as exc:
        print('Rotina interrompida:',exc)
        print('Confira o jogo e a evidencia em var/runs antes de iniciar outro lote.')
        return 1
    print('Atos concluidos:',result.get('completed_acts',0),'de',acts)
    print('Evidencias:',result.get('evidence_dir'))
    if not result.get('completed'):
        print('A tela final nao foi comprovada. Confira o jogo antes de continuar.')
    return 0 if result.get('completed') else 1


if __name__=='__main__':
    try:
        code=main()
    except KeyboardInterrupt:
        print('Interrompido. Confira o jogo antes de iniciar outro lote.')
        code=130
    if '--elevated' in sys.argv:
        try:input('Pressione Enter para fechar...')
        except (EOFError,KeyboardInterrupt):pass
    raise SystemExit(code)
