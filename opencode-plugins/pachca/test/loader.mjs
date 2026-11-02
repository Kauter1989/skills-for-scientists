const STUB = new URL("./opencode-plugin-stub.mjs", import.meta.url).href;

export async function resolve(specifier, context, nextResolve) {
  if (specifier === "@opencode/plugin") {
    return { url: STUB, shortCircuit: true };
  }
  return nextResolve(specifier, context);
}