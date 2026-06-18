"""
main.py — Eva AI Caller entry point.

Choose where and how Eva runs:

  1  Local — Terminal + Mic   (no frontend; mic input, audio on your device)
  2  Local — WebSocket        (frontend running on localhost connects here)
  3  Server — WebSocket       (frontend on a remote / same server connects here)
"""

class LocalTerminal:
    def run(self):
        from local import run_terminal_mode
        run_terminal_mode()

class LocalWebsocket:
    def run(self):
        from local import run_local_ws_mode
        run_local_ws_mode()

class ServerWebsocket:
    def run(self):
        import asyncio
        from server import main as server_main
        asyncio.run(server_main())


def main():
    '''Modify here if you want to run the code in local terminal, local websocket or server socket'''
    ServerWebsocket().run()
    # LocalWebsocket().run()


if __name__ == "__main__":
    main()