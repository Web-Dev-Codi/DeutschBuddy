# Textual CLI Commands Documentation

## Overview

Textual comes with a powerful command-line interface (CLI) tool called
`textual` that helps you build, debug, and manage Textual applications.
The CLI is part of the `textual-dev` package and provides various subcommands
for development workflows.

## Installation

To access the `textual` CLI, you need to install the `textual-dev` package:

```bash
pip install textual-dev
```

## Main CLI Help

```bash
textual --help
```

**Output:**

```text
Usage: textual [OPTIONS] COMMAND [ARGS]...

  Textual CLI.

Options:
  --version  Show the version and exit.
  --help     Show this message and exit.

Commands:
  console   Launch a Textual developer console.
  diagnose  Diagnose common problems.
  keys      Show key events.
  run       Run a Textual app.
  serve     Serve a Textual app as a web application.
```

## Commands

### 1. `textual run`

Run Textual applications from files or import paths.

#### Basic Usage

```bash
# Run a Python file containing a Textual app
textual run my_app.py

# Run an app from a Python import path
textual run music.play

# Run a specific app class or instance
textual run music.play:MusicPlayerApp
```

#### Development Mode

```bash
# Run with development features enabled
textual run --dev my_app.py
```

Development mode includes:

- Live CSS editing (changes to CSS files are reflected immediately)
- Integration with the debug console
- Enhanced logging capabilities

#### Command-line Scripts

```bash
# Run command-line scripts within Textual environment
textual run -c "print('Hello from Textual!')"
```

#### Run Command Options

```bash
textual run --help
```

### 2. `textual serve`

Serve Textual applications as web applications in a browser.

#### Basic Usage

```bash
# Serve a Python file
textual serve my_app.py

# Serve a command
textual serve "textual keys"

# Serve the Textual demo
textual serve "python -m textual"
```

#### Features

- Multiple instances can be served simultaneously
- Live reloading: refresh browser to see code changes
- Full terminal-to-web conversion

#### Serve Command Options

```bash
textual serve --help
```

### 3. `textual console`

Launch a debug console for development and debugging.

#### Basic Usage

```bash
# Start the debug console
textual console
```

#### Workflow

1. Terminal 1: `textual console`
2. Terminal 2: `textual run --dev my_app.py`
3. Any `print` statements or `textual.log` messages appear in the console

#### Options

##### Increase Verbosity

```bash
# Show verbose log messages
textual console -v
```

##### Decrease Verbosity

```bash
# Exclude specific message groups
textual console -x SYSTEM -x EVENT -x DEBUG -x INFO
```

Available message groups: `EVENT`, `DEBUG`, `INFO`, `WARNING`,
`ERROR`, `PRINT`, `SYSTEM`, `LOGGING`, `WORKER`

##### Custom Port

```bash
# Use custom port (useful if default port is occupied)
textual console --port 7342
textual run --dev --port 7342 my_app.py
```

### 4. `textual keys` - Display Key Events

Display key events to understand terminal key mappings.

#### Usage

```bash
textual keys
```

This command shows:

- What key combinations your terminal passes through
- How keys are named in Textual
- Useful for debugging keyboard input problems

### 5. `textual diagnose`

Diagnose common problems with Textual applications.

#### Usage

```bash
textual diagnose
```

**Purpose:**

- Check system compatibility
- Identify common configuration issues
- Generate diagnostic information for bug reports
- Recommended to run and include output when reporting bugs

## Logging and Debugging

### Using the Log Function

```python
from textual import log

def on_mount(self) -> None:
    log("Hello, World")                    # Simple string
    log(locals())                          # Log local variables
    log(children=self.children, pi=3.141592)  # Key/value pairs
    log(self.tree)                         # Rich renderables
```

### App and Widget Log Methods

```python
from textual.app import App

class LogApp(App):
    def on_load(self):
        self.log("In the log handler!", pi=3.141529)
    
    def on_mount(self):
        self.log(self.tree)
```

## Development Workflow

### Typical Development Setup

1. **Start Debug Console**

   ```bash
   textual console
   ```

2. **Run App in Development Mode**

   ```bash
   textual run --dev my_app.py
   ```

3. **Make Changes**

   - Edit CSS files for live styling updates
   - Edit Python files and restart to see changes
   - Use `print()` and `log()` for debugging

### Web Development Workflow

1. **Serve as Web App**

   ```bash
   textual serve my_app.py
   ```

2. **Open Browser**

   - Navigate to the provided URL
   - Refresh browser to see code changes

## Tips and Best Practices

- **Always use `--dev` flag** during development for debugging capabilities
- **Keep console running** in a separate terminal for continuous logging
- **Use `textual diagnose`** when troubleshooting issues
- **Serve as web app** for easier testing and sharing
- **Check `textual keys`** when debugging keyboard input problems

## Integration with Python

The `textual` CLI is equivalent to running Python directly but with additional
development features:

```bash
# These are equivalent:
python my_app.py
textual run my_app.py

# But textual run offers additional switches:
textual run --dev my_app.py  # Development mode
```

## Version Information

Check your Textual CLI version:

```bash
textual --version
```

## Additional Resources

- [Textual Documentation](https://textual.textualize.io/)
- [Devtools Guide](https://textual.textualize.io/guide/devtools/)
- [Getting Started](https://textual.textualize.io/getting_started/)
- [GitHub Repository](https://github.com/Textualize/textual)
