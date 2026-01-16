from codeop import compile_command
import sys
from _pyrepl.console import Console, Event
from _pyrepl.reader import Reader
from collections import deque
import js  # Pyodide's bridge to JavaScript
from pyodide.ffi import create_proxy


class BrowserConsole(Console):
    def __init__(self, term):
        # term is the xterm.js Terminal instance passed from JS
        self.term = term
        self.event_queue = deque()
        self.encoding = "utf-8"
        self.screen = []
        self.posxy = (0, 0)
        self.height, self.width = self.getheightwidth()
        self._resolve_input = None

    def getheightwidth(self):
        return self.term.rows, self.term.cols

    def refresh(self, screen, xy):
        # TODO: redraw screen
        pass

    def prepare(self):
        # TODO: setup
        pass

    def restore(self):
        # TODO: teardown
        pass

    def move_cursor(self, x, y):
        self.term.write(f"\x1b[{y + 1};{x + 1}H")
        self.posxy = (x, y)

    def set_cursor_vis(self, visible):
        self.term.write("\x1b[?25h" if visible else "\x1b[?25l")

    def beep(self):
        self.term.write("\x07")

    def clear(self):
        self.term.write("\x1b[2J\x1b[H")
        self.screen = []
        self.posxy = (0, 0)

    def flushoutput(self):
        pass  # xterm.js writes immediately

    def finish(self):
        pass

    def forgetinput(self):
        self.event_queue.clear()

    def push_char(self, char):
        js.console.log(f"Pushing char: {char}")
        self.event_queue.append(char)

        if self._resolve_input:
            resolve = self._resolve_input
            self._resolve_input = None
            resolve()

    def getpending(self):
        data = ""
        raw = b""
        while self.event_queue:
            c = self.event_queue.popleft()
            if isinstance(c, bytes):
                raw += c
                data += c.decode(self.encoding, errors="replace")
            else:
                raw += bytes([c])
                data += chr(c)
        return Event("key", data, raw)

    def wait(self, timeout=None):
        return len(self.event_queue) > 0

    async def get_event(self, block=True):
        js.console.log(
            f"Getting event, block={block}, queue size={len(self.event_queue)}"
        )
        if not block and not self.event_queue:
            return None

        while not self.event_queue:
            promise = js.Promise.new(
                create_proxy(
                    lambda resolve, reject: setattr(self, "_resolve_input", resolve)
                )
            )
            await promise

        char = self.event_queue.popleft()
        js.console.log(f"Got char: {char}")
        if isinstance(char, int):
            char_str = chr(char)
            raw = bytes([char])
        else:
            char_str = char
            raw = char.encode(self.encoding)
        event = Event("key", char_str, raw)
        js.console.log(f"Returning event: {event}")
        return event

    def repaint(self):
        pass


browser_console = BrowserConsole(js.term)


async def start_repl():

    class TermWriter:
        def write(self, data):
            browser_console.term.write(data.replace('\n', '\r\n'))
        def flush(self):
            pass
    
    sys.stdout = TermWriter()
    sys.stderr = TermWriter()

    def displayhook(value):
        if value is not None:
            repl_globals['_'] = value
            browser_console.term.write(repr(value) + "\r\n")

    sys.displayhook = displayhook

    repl_globals = {"__builtins__": __builtins__}
    browser_console.term.write("\x1b[32m>>> \x1b[0m")
    lines = []
    current_line = ""

    history = []
    history_index = 0

    while True:
        event = await browser_console.get_event(block=True)
        if event is None:
            continue

        char = event.data
        if char == '\x1b':
            # Might be an arrow key
            event2 = await browser_console.get_event(block=True)
            if event2 and event2.data == '[':
                event3 = await browser_console.get_event(block=True)
                if event3:
                    if event3.data == 'A':
                        # Up arrow
                        if history:
                            history_index = max(0, history_index - 1)
                            # Clear current line
                            browser_console.term.write('\r\x1b[K')
                            current_line = history[history_index]
                            browser_console.term.write("\x1b[32m>>> \x1b[0m" + current_line)
                    elif event3.data == 'B':
                        # Down arrow
                        if history:
                            history_index = min(len(history), history_index + 1)
                            # Clear current line
                            browser_console.term.write('\r\x1b[K')
                            if history_index < len(history):
                                current_line = history[history_index]
                            else:
                                current_line = ""
                            browser_console.term.write("\x1b[32m>>> \x1b[0m" + current_line)
                    # Left and Right arrows can be implemented similarly
            continue

        if char == '\r':
            browser_console.term.write("\r\n")
            js.console.log(f"Before append, lines: {repr(lines)}, current_line: {repr(current_line)}")

            lines.append(current_line)
            source = "\n".join(lines)
            js.console.log(f"Source: {repr(source)}")

            if not source.strip():
                lines = []
                current_line = ""
                browser_console.term.write("\x1b[32m>>> \x1b[0m")
                continue

            # If in multiline mode and user entered empty/whitespace line, execute
            if len(lines) > 1 and not current_line.strip():
                # Remove trailing empty lines
                while lines and not lines[-1].strip():
                    lines.pop()
                source = "\n".join(lines)
                try:
                    code = compile(source, "<console>", "single")
                    exec(code, repl_globals)
                    history.append(source)
                    history_index = len(history)
                except Exception as e:
                    browser_console.term.write(f"\x1b[31m{type(e).__name__}: {e}\x1b[0m\r\n")
                lines = []
                current_line = ""
                browser_console.term.write("\x1b[32m>>> \x1b[0m")
                continue
            
            try:
                code = compile_command(source, "<console>", "single")
                if code is None:
                    # Incomplete — need more input
                    browser_console.term.write("\x1b[32m... \x1b[0m    ")
                    current_line = "    "
                else:
                    # Complete code, execute it
                    try:
                        exec(code, repl_globals)
                        if source.strip():
                            history.append(source)
                            history_index = len(history)
                    except Exception as e:
                        browser_console.term.write(f"\x1b[31m{type(e).__name__}: {e}\x1b[0m\r\n")
                    lines = []
                    current_line = ""
                    browser_console.term.write("\x1b[32m>>> \x1b[0m")
            except SyntaxError as e:
                browser_console.term.write(f"\x1b[31mSyntaxError: {e}\x1b[0m\r\n")
                lines = []
                current_line = ""
                browser_console.term.write("\x1b[32m>>> \x1b[0m")
            except Exception as e:
                browser_console.term.write(f"\x1b[31mError: {e}\x1b[0m\r\n")
                lines = []
                current_line = ""
                browser_console.term.write("\x1b[32m>>> \x1b[0m")
        elif char == "\x7f":
            if current_line:
                current_line = current_line[:-1]
                browser_console.term.write("\b \b")
        else:
            current_line += char
            browser_console.term.write(char)                   
