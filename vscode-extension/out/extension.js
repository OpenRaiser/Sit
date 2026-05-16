"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const cp = __importStar(require("child_process"));
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
const vscode = __importStar(require("vscode"));
let output;
let statusItem;
function activate(context) {
    output = vscode.window.createOutputChannel("SitHub");
    statusItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 90);
    statusItem.command = "sithub.refreshStatus";
    statusItem.text = "$(pulse) SitHub";
    statusItem.tooltip = "Refresh SitHub Skill status";
    context.subscriptions.push(output, statusItem);
    context.subscriptions.push(vscode.commands.registerCommand("sithub.info", () => runInfo()), vscode.commands.registerCommand("sithub.validate", () => runValidate()), vscode.commands.registerCommand("sithub.test", () => runTest()), vscode.commands.registerCommand("sithub.diffHead", () => runDiff()), vscode.commands.registerCommand("sithub.refreshStatus", () => refreshStatus()));
    const watcher = vscode.workspace.createFileSystemWatcher("**/skill.yaml");
    context.subscriptions.push(watcher, watcher.onDidCreate(() => refreshStatus()), watcher.onDidChange(() => refreshStatus()), watcher.onDidDelete(() => refreshStatus()));
    refreshStatus();
}
function deactivate() {
    // Nothing to clean up beyond VS Code disposables.
}
async function runInfo() {
    await runJsonCommand("Info", ["info", ".", "--format", "json"], summarizeInfo);
}
async function runValidate() {
    await runTextCommand("Validate", ["validate", "."]);
    await refreshStatus();
}
async function runTest() {
    await runJsonCommand("Test", ["test", ".", "--format", "json"], summarizeTest);
    await refreshStatus();
}
async function runDiff() {
    const range = vscode.workspace.getConfiguration("sithub").get("defaultDiffRange", "HEAD~1..HEAD");
    await runJsonCommand(`Diff ${range}`, ["diff", range, "--format", "json"], summarizeDiff);
}
async function refreshStatus() {
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
    }
    catch (error) {
        statusItem.text = "$(warning) SitHub";
        statusItem.tooltip = error instanceof Error ? error.message : String(error);
        statusItem.show();
    }
}
async function runTextCommand(title, args) {
    output.show(true);
    try {
        const root = requireSkillRoot();
        outputHeader(title, root, args);
        const result = await runSit(args, root);
        appendIfPresent(result.stdout);
        appendIfPresent(result.stderr);
    }
    catch (error) {
        appendError(error);
    }
}
async function runJsonCommand(title, args, summarize) {
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
    }
    catch (error) {
        appendError(error);
    }
}
function outputHeader(title, root, args) {
    output.appendLine("");
    output.appendLine(`## ${title}`);
    output.appendLine(`root: ${root}`);
    output.appendLine(`command: ${[getSitPath(), ...getSitArgs(), ...args].join(" ")}`);
    output.appendLine("");
}
function summarizeInfo(payload) {
    return [
        `package: ${payload.package?.name ?? "<unknown>"}@${payload.package?.version ?? "<unknown>"}`,
        `validation: ${payload.validation?.status ?? "unknown"}`,
        `golden tests: ${payload.golden_tests?.status ?? "unknown"}`,
        `git dirty: ${payload.git?.dirty === true ? "yes" : payload.git?.dirty === false ? "no" : "unknown"}`
    ];
}
function summarizeTest(payload) {
    return [
        `validation: ${payload.validation?.status ?? "unknown"}`,
        `golden tests: ${payload.golden_tests?.status ?? "unknown"}`,
        `summary: ${payload.golden_tests?.summary ?? "<none>"}`
    ];
}
function summarizeDiff(payload) {
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
function runSit(args, cwd) {
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
function getSitPath() {
    return vscode.workspace.getConfiguration("sithub").get("sitPath", "sit");
}
function getSitArgs() {
    return vscode.workspace.getConfiguration("sithub").get("sitArgs", []);
}
function requireSkillRoot() {
    const root = findSkillRoot();
    if (!root) {
        throw new Error("No skill.yaml found. Open a Skill Package folder or a file inside one.");
    }
    return root;
}
function findSkillRoot() {
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
function findUp(start, filename) {
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
function appendIfPresent(text) {
    if (text.trim()) {
        output.appendLine(text.trimEnd());
    }
}
function appendError(error) {
    output.appendLine("ERROR");
    output.appendLine(error instanceof Error ? error.message : String(error));
    vscode.window.showErrorMessage(`SitHub command failed: ${error instanceof Error ? error.message : String(error)}`);
}
