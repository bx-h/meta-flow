export function parseOptions(argv, schema = {}) {
  const options = {};
  const rest = [];

  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (!token.startsWith("--")) {
      rest.push(token);
      continue;
    }
    if (token === "--") {
      rest.push(...argv.slice(index + 1));
      break;
    }

    const [rawName, inlineValue] = token.slice(2).split("=", 2);
    const negated = rawName.startsWith("no-");
    const name = toCamel(negated ? rawName.slice(3) : rawName);
    const kind = schema[name] || "boolean";

    if (negated) {
      options[name] = false;
      continue;
    }
    if (kind === "boolean") {
      options[name] = inlineValue === undefined ? true : inlineValue !== "false";
      continue;
    }
    if (inlineValue !== undefined) {
      options[name] = inlineValue;
      continue;
    }
    if (index + 1 >= argv.length) {
      throw new Error(`Missing value for --${rawName}`);
    }
    options[name] = argv[index + 1];
    index += 1;
  }

  return { options, rest };
}

export function toCamel(value) {
  return value.replace(/-([a-z])/g, (_, letter) => letter.toUpperCase());
}

export function helpRequested(argv) {
  return argv.includes("--help") || argv.includes("-h");
}
