export async function injectDice(pyodide) {
  const dice = await (await fetch('dice.py')).text();
  pyodide.FS.writeFile('/home/pyodide/dice.py', dice);
  pyodide.runPython('from dice import *');

  const readme = await (await fetch('README.md')).text();
  const help = readme
    .split(/[\n\r\f]+/)
	 .slice(2)
	 .join('\n')
	 .concat('\nThe original help utility has been renamed to _help');
  pyodide.runPython(`_help = help`);
  pyodide.runPython(`help = ShowStr("""${help}""")`);
}
