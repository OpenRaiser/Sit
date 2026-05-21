import * as cp from "child_process";
import * as fs from "fs";
import * as path from "path";
import * as vscode from "vscode";

type SitResult = {
  stdout: string;
  stderr: string;
};

let output: vscode.OutputChannel;
let statusItem: vscode.StatusBarItem;

export function activate(context: vscode.ExtensionContext): void {
  output = vscode.window.createOutputChannel("SitHub");
  statusItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 90);
  statusItem.command = "sithub.refreshStatus";
  statusItem.text = "$(pulse) SitHub";
  statusItem.tooltip = "Refresh SitHub Skill status";
  context.subscriptions.push(output, statusItem);

  context.subscriptions.push(
    vscode.commands.registerCommand("sithub.info", () => runInfo()),
    vscode.commands.registerCommand("sithub.validate", () => runValidate()),
    vscode.commands.registerCommand("sithub.test", () => runTest()),
    vscode.commands.registerCommand("sithub.diffHead", () => runDiff()),
    vscode.commands.registerCommand("sithub.refreshStatus", () => refreshStatus())
  );

  const watcher = vscode.workspace.createFileSystemWatcher("**/skill.yaml");
  context.subscriptions.push(
    watcher,
    watcher.onDidCreate(() => refreshStatus()),
    watcher.onDidChange(() => refreshStatus()),
    watcher.onDidDelete(() => refreshStatus())
  );

  refreshStatus();
}

export function deactivate(): void {
  // Nothing to clean up beyond VS Code disposables.
}

async function runInfo(): Promise<void> {
  await runJsonCommand("Info", ["info", ".", "--format", "json"], summarizeInfo);
}

async function runValidate(): Promise<void> {
  await runTextCommand("Validate", ["validate", "."]);
  await refreshStatus();
}

async function runTest(): Promise<void> {
  await runJsonCommand("Test", ["test", ".", "--format", "json"], summarizeTest);
  await refreshStatus();
}

async function runDiff(): Promise<void> {
  const range = vscode.workspace.getConfiguration("sithub").get<string>("defaultDiffRange", "HEAD~1..HEAD");
  await runJsonCommand(`Diff ${range}`, ["diff", range, "--format", "json"], summarizeDiff);
}

async function refreshStatus(): Promise<void> {
  const root = findSkillRoot();
  if (!root) {
    statusItem.text = "$(circle-slash) SitHub";
    statusItem.tooltip = "No skill.yaml found in this workspace";
    statusItem.show();
    return;
  }

  try {
    const result = await runSit(["info", ".", "--format", "json"], root);
    const payload = JSON.parse(result.stdout);
    const name = payload.package?.name ?? "Skill";
    const version = payload.package?.version ?? "<unknown>";
    const validation = payload.validation?.status ?? "unknown";
    const tests = payload.golden_tests?.status ?? "unknown";
    statusItem.text = validation === "pass" && tests === "pass" ? "$(check) SitHub" : "$(warning) SitHub";
    statusItem.tooltip = `${name}@${version} | validation: ${validation} | tests: ${tests}`;
    statusItem.show();
  } catch (error) {
    statusItem.text = "$(warning) SitHub";
    statusItem.tooltip = error instanceof Error ? error.message : String(error);
    statusItem.show();
  }
}

async function runTextCommand(title: string, args: string[]): Promise<void> {
  output.show(true);
  try {
    const root = requireSkillRoot();
    outputHeader(title, root, args);
    const result = await runSit(args, root);
    appendIfPresent(result.stdout);
    appendIfPresent(result.stderr);
  } catch (error) {
    appendError(error);
  }
}

async function runJsonCommand(title: string, args: string[], summarize: (payload: any) => string[]): Promise<void> {
  output.show(true);
  try {
    const root = requireSkillRoot();
    outputHeader(title, root, args);
    const result = await runSit(args, root);
    const payload = JSON.parse(result.stdout);
    for (const line of summarize(payload)) {
      output.appendLine(line);
    }
    output.appendLine("");
    output.appendLine(JSON.stringify(payload, null, 2));
    appendIfPresent(result.stderr);
  } catch (error) {
    appendError(error);
  }
}

function outputHeader(title: string, root: string, args: string[]): void {
  output.appendLine("");
  output.appendLine(`## ${title}`);
  output.appendLine(`root: ${root}`);
  output.appendLine(`command: ${[getSitPath(), ...getSitArgs(), ...args].join(" ")}`);
  output.appendLine("");
}

function summarizeInfo(payload: any): string[] {
  return [
    `package: ${payload.package?.name ?? "<unknown>"}@${payload.package?.version ?? "<unknown>"}`,
    `validation: ${payload.validation?.status ?? "unknown"}`,
    `golden tests: ${payload.golden_tests?.status ?? "unknown"}`,
    `git dirty: ${payload.git?.dirty === true ? "yes" : payload.git?.dirty === false ? "no" : "unknown"}`
  ];
}

function summarizeTest(payload: any): string[] {
  return [
    `validation: ${payload.validation?.status ?? "unknown"}`,
    `golden tests: ${payload.golden_tests?.status ?? "unknown"}`,
    `summary: ${payload.golden_tests?.summary ?? "<none>"}`
  ];
}

function summarizeDiff(payload: any): string[] {
  const lines = [
    `risk: ${payload.risk ?? "unknown"}`,
    `suggested bump: ${payload.suggested_bump ?? "unknown"}`
  ];
  const events = Array.isArray(payload.events) ? payload.events : [];
  for (const event of events.slice(0, 20)) {
    lines.push(`- ${event.message}`);
  }
  if (events.length > 20) {
    lines.push(`... ${events.length - 20} more events`);
  }
  return lines;
}

function runSit(args: string[], cwd: string): Promise<SitResult> {
  const command = getSitPath();
  const commandArgs = [...getSitArgs(), ...args];
  return new Promise((resolve, reject) => {
    cp.execFile(command, commandArgs, { cwd, maxBuffer: 1024 * 1024 * 4 }, (error, stdout, stderr) => {
      if (error) {
        reject(new Error([error.message, stderr, stdout].filter(Boolean).join("\n")));
        return;
      }
      resolve({ stdout, stderr });
    });
  });
}

function getSitPath(): string {
  return vscode.workspace.getConfiguration("sithub").get<string>("sitPath", "sit");
}

function getSitArgs(): string[] {
  return vscode.workspace.getConfiguration("sithub").get<string[]>("sitArgs", []);
}

function requireSkillRoot(): string {
  const root = findSkillRoot();
  if (!root) {
    throw new Error("No skill.yaml found. Open a Skill Package folder or a file inside one.");
  }
  return root;
}

function findSkillRoot(): string | undefined {
  const active = vscode.window.activeTextEditor?.document.uri;
  if (active?.scheme === "file") {
    const fromActive = findUp(path.dirname(active.fsPath), "skill.yaml");
    if (fromActive) {
      return fromActive;
    }
  }

  for (const folder of vscode.workspace.workspaceFolders ?? []) {
    const root = folder.uri.fsPath;
    if (fs.existsSync(path.join(root, "skill.yaml"))) {
      return root;
    }
  }
  return undefined;
}

function findUp(start: string, filename: string): string | undefined {
  let current = start;
  while (true) {
    if (fs.existsSync(path.join(current, filename))) {
      return current;
    }
    const parent = path.dirname(current);
    if (parent === current) {
      return undefined;
    }
    current = parent;
  }
}

function appendIfPresent(text: string): void {
  if (text.trim()) {
    output.appendLine(text.trimEnd());
  }
}

function appendError(error: unknown): void {
  output.appendLine("ERROR");
  output.appendLine(error instanceof Error ? error.message : String(error));
  vscode.window.showErrorMessage(`SitHub command failed: ${error instanceof Error ? error.message : String(error)}`);
}
