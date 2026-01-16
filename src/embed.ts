import type { PyodideInterface } from "pyodide";
import { loadPyodide } from "pyodide";
import { Terminal } from '@xterm/xterm';

let pyodidePromise: Promise<PyodideInterface> | null = null;

let currentOutput: Terminal | null = null;

const catppuccinMocha = {
  background: '#1e1e2e',
  foreground: '#cdd6f4',
  cursor: '#f5e0dc',
  cursorAccent: '#1e1e2e',
  selectionBackground: '#585b70',
  black: '#45475a',
  red: '#f38ba8',
  green: '#a6e3a1',
  yellow: '#f9e2af',
  blue: '#89b4fa',
  magenta: '#f5c2e7',
  cyan: '#94e2d5',
  white: '#bac2de',
  brightBlack: '#585b70',
  brightRed: '#f38ba8',
  brightGreen: '#a6e3a1',
  brightYellow: '#f9e2af',
  brightBlue: '#89b4fa',
  brightMagenta: '#f5c2e7',
  brightCyan: '#94e2d5',
  brightWhite: '#a6adc8',
};

function getPyodide(): Promise<PyodideInterface> {
    if (!pyodidePromise) {
        pyodidePromise = loadPyodide({
            indexURL: "https://cdn.jsdelivr.net/pyodide/v0.29.1/full/",
            stdout: (text) => {
                if (currentOutput) {
                    currentOutput.write(text + "\r\n");
                }
            },
            stderr: (text) => {
                if (currentOutput) {
                    currentOutput.write(text + "\r\n");
                }
            },
        });
    }
    return pyodidePromise;
}

function init() {
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", setup);
    } else {
        setup();
    }
}

async function createRepl(container: HTMLElement) {
    const term = new Terminal({
        cursorBlink: true,
        fontSize: 14,
        fontFamily: 'monospace',
        theme: catppuccinMocha,

    });
    term.open(container);
    term.write('Loading Pyodide...\r\n');

    const pyodide = await getPyodide();
    await pyodide.loadPackage("micropip");

    // Expose terminal to Python
    (globalThis as any).term = term;

    // Load the browser console code
    const response = await fetch('/python/console.py');
    const consoleCode = await response.text();
    pyodide.runPython(consoleCode);

    // Start the REPL
    pyodide.runPythonAsync('await start_repl()');

    // Get the BrowserConsole class
    const browserConsole = pyodide.globals.get('browser_console');

    //Keep browserConsole alive
    (globalThis as any).browserConsole = browserConsole;

    term.onData((data) => {
        for (const char of data) {
            browserConsole.push_char(char.charCodeAt(0));
        }
    });

    term.write('Ready.\r\n');
}


async function setup() {
    const containers = document.querySelectorAll<HTMLElement>(".pyrepl");

    if (containers.length === 0) {
        console.warn("pyrepl-web: no .pyrepl elements found");
        return;
    }

    containers.forEach(createRepl);
}

init();

