// CCOM v0.1 - Claude Code Orchestrator and Memory (200 lines total)
const fs = require("fs");
const path = require("path");

class CCOM {
  constructor() {
    this.memoryPath = path.join(process.cwd(), ".claude", "memory.json");
    this.memory = this.loadMemory();
    this.setupHooks();
    this.autoDisplayMemory(); // Auto-display on load
  }

  // Core memory functions
  loadMemory() {
    try {
      const data = fs.readFileSync(this.memoryPath, "utf8");
      return JSON.parse(data);
    } catch (e) {
      // First run or corrupted - create new
      const empty = this.createEmptyMemory();
      this.saveMemory(empty);
      return empty;
    }
  }

  saveMemory(memory = this.memory) {
    try {
      fs.writeFileSync(this.memoryPath, JSON.stringify(memory, null, 2));
      this.memory = memory;
      return true;
    } catch (e) {
      console.error("Failed to save memory:", e.message);
      return false;
    }
  }

  createEmptyMemory() {
    return {
      version: "0.1",
      project: {
        name: path.basename(process.cwd()),
        created: new Date().toISOString().split("T")[0],
      },
      features: {},
    };
  }

  // Feature management
  rememberFeature(name, data = {}) {
    // Check for exact duplicate
    if (this.checkDuplicate(name)) {
      console.log(`⚠️  Duplicate detected: "${name}" already exists!`);
      return false;
    }

    this.memory.features[name] = {
      created: new Date().toISOString(),
      description: data.description || "",
      files: data.files || [],
      userTerm: data.userTerm || name,
    };

    this.saveMemory();
    console.log(`✅ Remembered: ${name}`);
    return true;
  }

  checkDuplicate(name) {
    const normalized = name.toLowerCase().trim();

    for (const existing of Object.keys(this.memory.features)) {
      if (existing.toLowerCase().trim() === normalized) {
        return existing;
      }

      // Also check user terms
      const feature = this.memory.features[existing];
      if (
        feature.userTerm &&
        feature.userTerm.toLowerCase().trim() === normalized
      ) {
        return existing;
      }
    }

    return false;
  }

  // Context injection for Claude
  getContextSummary() {
    const featureCount = Object.keys(this.memory.features).length;

    if (featureCount === 0) {
      return `Starting fresh project: ${this.memory.project.name}`;
    }

    const features = Object.entries(this.memory.features)
      .map(([name, data]) => {
        const userTerm =
          data.userTerm !== name ? ` (aka "${data.userTerm}")` : "";
        return `• ${name}${userTerm}: ${data.description || "No description"}`;
      })
      .join("\n");

    return `
🧠 Memory Loaded: ${this.memory.project.name}
Features built (${featureCount}):
${features}

⚠️ Check for duplicates before creating new features!
    `.trim();
  }

  // Display functions
  showMemory() {
    console.log("\n📝 Memory Contents");
    console.log("━".repeat(40));
    console.log(`Project: ${this.memory.project.name}`);
    console.log(`Created: ${this.memory.project.created}`);
    console.log(`\nFeatures (${Object.keys(this.memory.features).length}):`);

    for (const [name, data] of Object.entries(this.memory.features)) {
      console.log(`\n  ${name}`);
      if (data.userTerm && data.userTerm !== name) {
        console.log(`    Alias: "${data.userTerm}"`);
      }
      if (data.description) {
        console.log(`    Description: ${data.description}`);
      }
      if (data.files && data.files.length > 0) {
        console.log(`    Files: ${data.files.join(", ")}`);
      }
      console.log(`    Created: ${data.created}`);
    }
    console.log("━".repeat(40));
  }

  clearMemory() {
    const empty = this.createEmptyMemory();
    this.saveMemory(empty);
    console.log("✅ Memory cleared");
  }

  // Auto-display memory on session start
  autoDisplayMemory() {
    const featureCount = Object.keys(this.memory.features).length;

    if (featureCount === 0) {
      console.log(`📝 Starting fresh project: ${this.memory.project.name}`);
      return;
    }

    console.log("\n🧠 MEMORY LOADED - Existing Features:");
    console.log("═".repeat(50));

    for (const [name, data] of Object.entries(this.memory.features)) {
      console.log(`• ${name}`);
      if (data.description) {
        console.log(`  Description: ${data.description}`);
      }
      if (data.files && data.files.length > 0) {
        console.log(`  Files: ${data.files.join(", ")}`);
      }
      console.log(`  Created: ${data.created}`);
      console.log("");
    }

    console.log("⚠️  CHECK FOR DUPLICATES BEFORE CREATING NEW FEATURES!");
    console.log("═".repeat(50));
    console.log("");
  }

  // Hook setup for Claude Code integration
  setupHooks() {
    // This would integrate with Claude Code's hook system
    // For v0.1, we just provide the methods

    // On session start
    this.onSessionStart = () => {
      const context = this.getContextSummary();
      console.log(context);
      return context;
    };

    // On command received
    this.onCommand = (command) => {
      const lower = command.toLowerCase();

      // Check for memory commands
      if (lower.includes("remember this as")) {
        const match = command.match(/remember this as[:\s]+(.+)/i);
        if (match) {
          this.rememberFeature(match[1].trim());
        }
      } else if (
        lower.includes("what have we built") ||
        lower.includes("show memory")
      ) {
        this.showMemory();
      } else if (lower.includes("clear memory")) {
        this.clearMemory();
      } else {
        // Check for duplicate creation attempts
        const createWords = ["create", "add", "build", "make"];
        for (const word of createWords) {
          if (lower.includes(word)) {
            const possibleFeature = lower
              .replace(new RegExp(word, "g"), "")
              .trim();
            const duplicate = this.checkDuplicate(possibleFeature);
            if (duplicate) {
              console.log(
                `⚠️  Similar feature exists: "${duplicate}". Consider enhancing it instead.`,
              );
            }
          }
        }
      }
    };
  }
}

// Export for use
module.exports = CCOM;

// If run directly, show status
if (require.main === module) {
  const ccom = new CCOM();

  const args = process.argv.slice(2);
  const command = args[0];

  switch (command) {
    case "start":
      console.log(ccom.onSessionStart());
      break;
    case "memory":
      ccom.showMemory();
      break;
    case "clear":
      ccom.clearMemory();
      break;
    case "remember":
      const name = args.slice(1).join(" ");
      if (name) {
        ccom.rememberFeature(name);
      } else {
        console.log("Usage: node ccom.js remember <feature-name>");
      }
      break;
    case "check":
      const checkName = args.slice(1).join(" ");
      if (checkName) {
        const duplicate = ccom.checkDuplicate(checkName);
        if (duplicate) {
          console.log(`EXISTS: "${duplicate}" already exists`);
          process.exit(1);
        } else {
          console.log(`CLEAR: No duplicate found for "${checkName}"`);
          process.exit(0);
        }
      } else {
        console.log("Usage: node ccom.js check <feature-name>");
      }
      break;
    default:
      console.log(`
CCOM v0.1 - Claude Code Orchestrator and Memory

Commands:
  node ccom.js start    - Show context summary
  node ccom.js memory   - Display all remembered features
  node ccom.js clear    - Clear memory (start fresh)
  node ccom.js remember <name> - Remember a feature
      `);
  }
}
