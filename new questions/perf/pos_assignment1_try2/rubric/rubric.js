
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, HeadingLevel, BorderStyle, WidthType, ShadingType, LevelFormat,
  PageBreak
} = require('docx');
const fs = require('fs');

// ── palette ───────────────────────────────────────────────────────────────────
const NAVY    = "2E4057";
const TEAL    = "1A6B8A";
const GREEN   = "1E6B45";
const RED     = "8B1A1A";
const AMBER   = "8B6000";
const LGRAY   = "F2F3F4";
const MARKS   = "EBF5FB";
const WHITE   = "FFFFFF";
const CODE_BG = "F7F9FA";
const CODE_FG = "1A3A4A";
const GREEN_BG= "EAF5EE";
const AMBER_BG= "FEF9E7";
const RED_BG  = "FDEDEC";

// ── border helpers ────────────────────────────────────────────────────────────
const thinBorder  = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const thinBorders = { top: thinBorder, bottom: thinBorder, left: thinBorder, right: thinBorder };
const noBorder    = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
const noBorders   = { top: noBorder, bottom: noBorder, left: noBorder, right: noBorder };

// ── basic helpers ─────────────────────────────────────────────────────────────
const gap  = () => new Paragraph({ spacing: { before: 60, after: 60 }, children: [new TextRun("")] });
const rule = () => new Paragraph({
  spacing: { before: 200, after: 200 },
  border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: "CCCCCC", space: 1 } },
  children: [new TextRun("")]
});
const pageBreak = () => new Paragraph({ children: [new PageBreak()] });

const run = (text, opts = {}) => new TextRun({
  text, font: "Arial",
  size:    opts.sz     || 20,
  bold:    opts.bold   || false,
  italics: opts.italic || false,
  color:   opts.color  || "000000",
});

const body = (text, opts = {}) => new Paragraph({
  spacing: { before: 60, after: 60 },
  children: [run(text, opts)]
});

const mono = (text) => new Paragraph({
  spacing: { before: 30, after: 30 },
  indent:  { left: 360 },
  shading: { fill: CODE_BG, type: ShadingType.CLEAR },
  children: [new TextRun({ text, font: "Courier New", size: 17, color: CODE_FG })]
});

const bullet = (text, lvl, bold) => new Paragraph({
  numbering: { reference: "bullets", level: lvl || 0 },
  spacing: { before: 40, after: 40 },
  children: [run(text, { bold: bold || false })]
});

const numbered = (text, lvl) => new Paragraph({
  numbering: { reference: "numbers", level: lvl || 0 },
  spacing: { before: 40, after: 40 },
  children: [run(text)]
});

// ── labelled callout box ──────────────────────────────────────────────────────
// color: 'green' | 'amber' | 'red'
function callout(label, lines, color) {
  const fills   = { green: GREEN_BG, amber: AMBER_BG, red: RED_BG };
  const borders = { green: GREEN,    amber: AMBER,    red: RED    };
  const fill   = fills[color]   || GREEN_BG;
  const accent = borders[color] || GREEN;
  return lines.map((text, i) => new Paragraph({
    spacing: { before: i === 0 ? 80 : 0, after: i === lines.length - 1 ? 80 : 0 },
    indent:  { left: 400 },
    shading: { fill, type: ShadingType.CLEAR },
    border:  { left: { style: BorderStyle.SINGLE, size: 16, color: accent, space: 8 } },
    children: i === 0
      ? [new TextRun({ text: label + "  ", font: "Arial", size: 18, bold: true, color: accent }),
         new TextRun({ text, font: "Arial", size: 18, color: "333333" })]
      : [new TextRun({ text: "\u00A0\u00A0\u00A0\u00A0\u00A0\u00A0" + text, font: "Arial", size: 18, color: "333333" })]
  }));
}

// ── marks band box ────────────────────────────────────────────────────────────
function marksBand(bands) {
  // bands: [{range:"3-4", label:"Full marks", desc:"...", color:"green"}, ...]
  const cols = [1200, 2000, 6160];
  return new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: cols,
    rows: [
      new TableRow({ children: [
        thcell("Marks",   cols[0]),
        thcell("Level",   cols[1]),
        thcell("Criteria", cols[2]),
      ]}),
      ...bands.map(b => {
        const fills = { green: GREEN_BG, amber: AMBER_BG, red: RED_BG };
        const colors = { green: GREEN, amber: AMBER, red: RED };
        const fill  = fills[b.color]  || LGRAY;
        const color = colors[b.color] || "555555";
        return new TableRow({ children: [
          colorCell(b.range, cols[0], fill, color, true),
          colorCell(b.label, cols[1], fill, color, false),
          colorCell(b.desc,  cols[2], fill, "333333", false),
        ]});
      })
    ]
  });
}

function colorCell(text, w, fill, color, center) {
  return new TableCell({
    borders: thinBorders,
    width:   { size: w, type: WidthType.DXA },
    shading: { fill, type: ShadingType.CLEAR },
    margins: { top: 80, bottom: 80, left: 120, right: 120 },
    children: [new Paragraph({
      alignment: center ? AlignmentType.CENTER : AlignmentType.LEFT,
      children:  [new TextRun({ text, font: "Arial", size: 18, bold: center, color })]
    })]
  });
}

function thcell(text, w) {
  return new TableCell({
    borders: thinBorders,
    width: { size: w, type: WidthType.DXA },
    shading: { fill: NAVY, type: ShadingType.CLEAR },
    margins: { top: 80, bottom: 80, left: 120, right: 120 },
    children: [new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [new TextRun({ text, font: "Arial", size: 19, bold: true, color: WHITE })]
    })]
  });
}

function tcell(text, w, fill, bold, center) {
  return new TableCell({
    borders: thinBorders,
    width: { size: w, type: WidthType.DXA },
    shading: { fill: fill || WHITE, type: ShadingType.CLEAR },
    margins: { top: 80, bottom: 80, left: 120, right: 120 },
    children: [new Paragraph({
      alignment: center ? AlignmentType.CENTER : AlignmentType.LEFT,
      children: [new TextRun({ text, font: "Arial", size: 18, bold: bold || false })]
    })]
  });
}

// ── question section header ───────────────────────────────────────────────────
function qHeader(num, title, marks) {
  return new Paragraph({
    spacing: { before: 280, after: 100 },
    border:  { left: { style: BorderStyle.SINGLE, size: 22, color: TEAL, space: 10 } },
    children: [
      new TextRun({ text: `Q${num}  `, font: "Arial", size: 26, bold: true, color: NAVY }),
      new TextRun({ text: title,       font: "Arial", size: 26, bold: true, color: NAVY }),
      new TextRun({ text: `   [${marks} marks]`, font: "Arial", size: 20, color: "888888" }),
    ]
  });
}

// ── answer block (green shaded) ───────────────────────────────────────────────
function answerBlock(label, items) {
  const rows = [];
  rows.push(new Paragraph({
    spacing: { before: 80, after: 40 },
    children: [new TextRun({ text: label, font: "Arial", size: 19, bold: true, color: GREEN })]
  }));
  rows.push(...items);
  return rows;
}

// ── Q7 answer table ───────────────────────────────────────────────────────────
function q7Table() {
  const rows_data = [
    ["page-faults",          "↓  Down",         GREEN_BG, GREEN,
     "Flat pre-allocated storage removes per-enqueue heap calls. All pages are mapped at construction; the OS is never interrupted again during the run."],
    ["instructions",         "↓  Down",         GREEN_BG, GREEN,
     "Eliminating new/delete removes glibc malloc internals from the hot path. The tight acquire-release loop executes fewer instructions per item than the seq_cst + malloc path."],
    ["IPC  (insn per cycle)", "↓  Down  (or ≈)", AMBER_BG, AMBER,
     "Producers now spin in a tighter CAS loop with almost no instructions between attempts. Very few instructions execute per cycle, but each one is useful. Low IPC is not a sign of slowness here."],
    ["sys time",              "↓  Down sharply", GREEN_BG, GREEN,
     "High sys time in the flawed version came from glibc malloc falling back to kernel-level mmap/brk calls and arena locks. Flat allocation removes all of this."],
    ["Throughput",            "↑  Up",           GREEN_BG, GREEN,
     "Fewer cycles wasted on false-sharing cache misses, pipeline-draining fences, and heap allocator overhead means more items processed per second."],
  ];
  return new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: [2200, 1600, 5560],
    rows: [
      new TableRow({ children: [thcell("Counter", 2200), thcell("Direction", 1600), thcell("Explanation", 5560)] }),
      ...rows_data.map(([counter, dir, fill, color, explanation]) =>
        new TableRow({ children: [
          colorCell(counter,     2200, LGRAY,  "333333", false),
          colorCell(dir,         1600, fill,   color,    false),
          colorCell(explanation, 5560, WHITE,  "333333", false),
        ]})
      )
    ]
  });
}

// ── marks summary table ───────────────────────────────────────────────────────
const marksSummary = new Table({
  width: { size: 9360, type: WidthType.DXA },
  columnWidths: [900, 6960, 1500],
  rows: [
    new TableRow({ children: [thcell("Q", 900), thcell("Topic", 6960), thcell("Marks", 1500)] }),
    ...[
      ["Q1", "First-pass triage with perf stat",               "4"],
      ["Q2", "Locating the hot function with perf report",      "5"],
      ["Q3", "Diagnosing bottlenecks with perf annotate",       "6"],
      ["Q4", "Understanding the atomic memory ordering flaw",   "6"],
      ["Q5", "Heap allocation and kernel overhead",             "5"],
      ["Q6", "Proposing and justifying all three fixes",        "7"],
      ["Q7", "Interpreting perf stat counters after fixes",     "7"],
      ["",   "Total",                                          "40"],
    ].map(([q, desc, m]) => new TableRow({ children: [
      tcell(q,    900,  LGRAY, true,  true),
      tcell(desc, 6960, WHITE, false, false),
      tcell(m,    1500, MARKS, true,  true),
    ]}))
  ]
});

// ══════════════════════════════════════════════════════════════════════════════
// DOCUMENT
// ══════════════════════════════════════════════════════════════════════════════
const doc = new Document({
  numbering: {
    config: [
      { reference: "bullets",
        levels: [
          { level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 540, hanging: 260 } } } },
          { level: 1, format: LevelFormat.BULLET, text: "–", alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 900, hanging: 260 } } } },
        ]
      },
      { reference: "numbers",
        levels: [
          { level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 540, hanging: 260 } } } },
        ]
      },
    ]
  },
  styles: {
    default: { document: { run: { font: "Arial", size: 20 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 30, bold: true, font: "Arial" },
        paragraph: { spacing: { before: 280, after: 120 }, outlineLevel: 0 } },
    ]
  },
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 1080, right: 1080, bottom: 1080, left: 1080 }
      }
    },
    children: [

      // ── Cover ─────────────────────────────────────────────────────────────
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 0, after: 80 },
        children: [new TextRun({ text: "CS 4XX  —  Systems Performance Engineering", font: "Arial", size: 26, bold: true, color: NAVY })] }),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 0, after: 80 },
        children: [new TextRun({ text: "Assignment 1  —  Instructor Rubric", font: "Arial", size: 36, bold: true, color: TEAL })] }),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 0, after: 80 },
        children: [new TextRun({ text: "CONFIDENTIAL  —  Do not distribute to students", font: "Arial", size: 20, bold: true, italics: true, color: RED })] }),
      gap(),
      body("This document contains model answers and grading bands for all seven questions. Each question lists the key ideas required for full marks, followed by a three-band rubric (full / partial / minimal). Award marks holistically within each band — a student does not need to use exact wording.", { italic: true }),
      gap(),
      marksSummary,
      gap(),
      rule(),

      // ══════════════════════════════════════════════════════════════════════
      // Q1
      // ══════════════════════════════════════════════════════════════════════
      qHeader(1, "First-pass triage with perf stat", "4 marks"),
      gap(),

      ...answerBlock("Model Answer", [
        body("Expected IPC output (representative — exact numbers vary by machine):", { bold: true }),
        mono("15,123,213,204      instructions    #    0.25  insn per cycle"),
        mono("      14.757929000 seconds user"),
        mono("       8.603527000 seconds sys"),
        gap(),
        body("Part A — IPC interpretation:"),
        bullet("A healthy IPC on a modern out-of-order core is 2–4. An IPC of ~0.25 means the CPU completes only one instruction for every four clock cycles."),
        bullet("This indicates the CPU is almost entirely stalled — it has instructions to execute but cannot because it is waiting for memory operands to arrive from the cache hierarchy or for a pipeline hazard to clear."),
        bullet("The processor is not compute-bound; it is memory/synchronisation-bound."),
        gap(),
        body("Part B — sys time interpretation:"),
        bullet("A lock-free data structure should never enter the kernel. Sys time above ~0.1 s is a red flag."),
        bullet("The most likely cause is dynamic memory allocation: new LogEntry() inside enqueue() calls glibc malloc, which under multi-threaded contention falls back to mmap or brk system calls and acquires internal per-arena locks — both kernel operations."),
        bullet("Students do not need to name malloc specifically at this stage; crediting any answer that connects sys time to hidden kernel activity is correct."),
      ]),
      gap(),
      marksBand([
        { range: "3–4", label: "Full",    color: "green",
          desc: "Correctly identifies low IPC and explains it as a memory/stall issue, not a compute issue. Identifies high sys time as unexpected for a lock-free structure and offers a plausible cause (allocation or kernel calls)." },
        { range: "1–2", label: "Partial", color: "amber",
          desc: "Reads IPC and notes it is low, but explanation is vague (e.g. 'the code is slow'). May note sys time without connecting it to allocation." },
        { range: "0",   label: "Minimal", color: "red",
          desc: "Pastes output only with no meaningful interpretation, or misreads which metric is IPC." },
      ]),
      gap(), rule(),

      // ══════════════════════════════════════════════════════════════════════
      // Q2
      // ══════════════════════════════════════════════════════════════════════
      qHeader(2, "Locating the hot function with perf report", "5 marks"),
      gap(),

      ...answerBlock("Model Answer", [
        body("Expected top of perf report (representative):"),
        mono("  42.86%  ipc_bench  ipc_bench  [.] producer_thread(...)"),
        mono("   5.56%  ipc_bench  libc.so.6  [.] _int_malloc"),
        mono("   1.10%  ipc_bench  [unknown]  [k] 0xffffffff..."),
        gap(),
        body("Part A — hot symbol:"),
        bullet("producer_thread dominates because -O3 inlined enqueue() into it. The real work (atomic CAS, heap allocation, data copy) now executes inside producer_thread from the profiler's perspective."),
        bullet("The presence of _int_malloc in the top three confirms that heap allocation is consuming significant cycles even after inlining — it is not fast enough to disappear into noise."),
        gap(),
        body("Part B — why perf report is insufficient:"),
        bullet("perf report shows overhead per symbol. After inlining, everything inside enqueue() appears as producer_thread, so the report cannot tell you which specific lines or instructions inside that function are expensive."),
        bullet("perf annotate maps cycle counts to individual assembly instructions and back to source lines. This is necessary to determine which of the many operations inside producer_thread — the atomic load, the CAS, the division, the malloc — is actually burning cycles."),
      ]),
      gap(),
      marksBand([
        { range: "4–5", label: "Full",    color: "green",
          desc: "Identifies producer_thread and/or _int_malloc as top symbols, explains inlining correctly, and clearly states that perf annotate is needed to go further and why." },
        { range: "2–3", label: "Partial", color: "amber",
          desc: "Identifies the hot symbol but does not explain inlining, OR explains inlining without identifying the correct symbol." },
        { range: "0–1", label: "Minimal", color: "red",
          desc: "Cannot identify the hot symbol, or confuses perf report and perf annotate." },
      ]),
      gap(), rule(),

      // ══════════════════════════════════════════════════════════════════════
      // Q3
      // ══════════════════════════════════════════════════════════════════════
      qHeader(3, "Diagnosing bottlenecks with perf annotate", "6 marks"),
      gap(),

      ...answerBlock("Model Answer", [
        body("The three assembly hotspots and their explanations:"),
        gap(),
        body("Hotspot 1 — Memory load stall on head_ (~28–30%)", { bold: true }),
        mono(" 29.52%  mov   0x0(%r13),%rsi        ; head_.load()"),
        bullet("head_ and tail_ sit adjacent in memory, fitting on a single 64-byte cache line."),
        bullet("Producers modify tail_; the consumer modifies head_. Because they share a cache line, every consumer write to head_ forces the MESI protocol to mark that line as Invalid (I) in the producer core's L1/L2 cache."),
        bullet("The next time any producer tries to read head_, its core must fetch the line from another core's cache over the cache interconnect — a slow operation (tens to hundreds of cycles). This is called false sharing: two unrelated variables fighting over the same physical cache line."),
        bullet("perf attributes the stall cycles to the instruction after the load (the subtraction), because the CPU issues the load speculatively and only stalls when it tries to use the result. This is why the mov appears cheap and the sub appears expensive."),
        gap(),
        body("Hotspot 2 — CAS branch misprediction (~29–48%)", { bold: true }),
        mono("  0.13%  lock  cmpxchg %rdx,(%rbx)"),
        mono(" 29.87%  jne   <retry>"),
        bullet("With 4 producers hammering tail_ simultaneously, the compare_exchange_weak fails the majority of the time. On failure, jne branches back to the top of the retry loop."),
        bullet("The CPU's branch predictor cannot determine whether the next CAS will succeed or fail — it is essentially random. Constant mispredictions cause repeated pipeline flushes, each costing 15–20 cycles."),
        bullet("perf attributes stall cycles to jne rather than lock cmpxchg because the cmpxchg itself executes and completes; it is the pipeline flush triggered by the mispredicted branch that burns the cycles."),
        gap(),
        body("Hotspot 3 — 64-bit integer division (~11–12%)", { bold: true }),
        mono("  0.00%  divq   0x10(%r12)"),
        mono(" 11.53%  mov    %rdx,%r15"),
        bullet("The source line is: size_t index = current_tail % capacity_;"),
        bullet("The % operator on a size_t with a runtime value compiles to a divq instruction on x86_64. Unlike addition or multiplication, integer division is not pipelined — the hardware division unit stalls the execution port for 30 to 90 clock cycles depending on operand size."),
        bullet("On the hot path of a ring buffer, paying 30–90 cycles just to compute an array index on every single enqueue is a significant waste."),
      ]),
      gap(),
      marksBand([
        { range: "5–6", label: "Full",    color: "green",
          desc: "Correctly identifies all three hotspot instructions, names false sharing and the MESI protocol for the load stall, explains that the branch (not the cmpxchg) carries stall cycles due to pipeline flush from misprediction, and identifies % capacity_ as the source of divq." },
        { range: "3–4", label: "Partial", color: "amber",
          desc: "Correctly explains two of the three hotspots. The third may be identified but poorly explained, or the student identifies the cmpxchg as the bottleneck rather than the jne." },
        { range: "0–2", label: "Minimal", color: "red",
          desc: "Can paste the assembly lines but cannot explain why they are expensive, or confuses the cause of the stalls." },
      ]),
      gap(), rule(),

      // ══════════════════════════════════════════════════════════════════════
      // Q4
      // ══════════════════════════════════════════════════════════════════════
      qHeader(4, "Understanding the atomic memory ordering flaw", "6 marks"),
      gap(),

      ...answerBlock("Model Answer", [
        body("Part A — what seq_cst forces the CPU to do:"),
        bullet("Modern CPUs use a store buffer: writes are placed in a small per-core queue and flushed to the L1 cache lazily, allowing the core to continue executing instructions without waiting for the write to propagate."),
        bullet("seq_cst breaks this optimisation. On x86_64, a seq_cst store (or any atomic RMW like compare_exchange) emits a LOCK prefix, which forces the CPU to drain its store buffer completely before the instruction is considered complete. No subsequent instruction may execute until all pending writes are visible to all cores globally."),
        bullet("This is called a full memory fence or pipeline drain. It is expensive because it turns what could be a fire-and-forget write into a synchronous, globally-ordered event."),
        bullet("seq_cst also prevents the compiler from reordering any non-atomic memory accesses across the atomic operation, further limiting instruction-level parallelism."),
        gap(),
        body("Part B — acquire-release semantics and why they are sufficient:"),
        bullet("An acquire load guarantees that all memory reads and writes that appear after it in program order will not be reordered before it. It creates a happens-after fence. On x86 this requires no hardware instruction beyond a normal mov, because x86 loads already have acquire semantics by default."),
        bullet("A release store guarantees that all memory reads and writes that appear before it in program order will not be reordered after it. It creates a happens-before fence. On x86 this is also a normal mov, since x86 stores are release by default."),
        bullet("For a producer-consumer queue: the producer writes the data to the slot, then does a release store to mark it ready. The consumer does an acquire load to read the ready flag, then reads the slot data. The release-acquire pair creates a happens-before edge: everything the producer wrote before the release is guaranteed to be visible to the consumer after the acquire."),
        bullet("No global ordering across all threads is needed — only this directed edge between producer and consumer. seq_cst provides global ordering across all threads, which is unnecessary and costly."),
      ]),
      gap(),
      marksBand([
        { range: "5–6", label: "Full",    color: "green",
          desc: "Correctly explains store buffer draining and pipeline fences for seq_cst. Correctly defines acquire (prevents later reads moving before it) and release (prevents earlier writes moving after it). Explains the happens-before edge between producer and consumer and why global ordering is unnecessary." },
        { range: "3–4", label: "Partial", color: "amber",
          desc: "Correctly explains one of the two parts. May describe seq_cst as 'heavy' without specifying store buffers, or may define acquire/release without connecting them to the producer-consumer ordering guarantee." },
        { range: "0–2", label: "Minimal", color: "red",
          desc: "Confuses memory_order levels, or provides only a dictionary-level definition without explaining hardware implications." },
      ]),
      gap(), rule(),

      // ══════════════════════════════════════════════════════════════════════
      // Q5
      // ══════════════════════════════════════════════════════════════════════
      qHeader(5, "Heap allocation and kernel overhead", "5 marks"),
      gap(),

      ...answerBlock("Model Answer", [
        body("Part A — virtual destructor cost:"),
        bullet("A virtual destructor requires the compiler to embed a vtable pointer inside every instance of the struct. On a 64-bit system this adds 8 bytes to each LogEntry and, more importantly, each object's first 8 bytes now contain an address rather than data."),
        bullet("Cache performance impact: storage_ is an array of pointers to heap objects. To read the timestamp of an entry, the CPU must load the pointer from the array (one cache line fetch), then follow the pointer to a potentially random heap address (a second cache line fetch, almost certainly an L1 miss). This is called pointer chasing and it serialises memory access — the second fetch cannot begin until the first completes."),
        bullet("The virtual destructor also prevents the compiler from making struct copies with SIMD (vectorised) instructions, because the presence of a vtable pointer makes the type non-trivially-copyable."),
        gap(),
        body("Part B — heap allocator contention and kernel overhead:"),
        bullet("glibc malloc organises the heap into per-thread arenas to reduce contention. Under moderate load each producer uses its own arena. Under heavy load (4 threads, tight loop) arenas become exhausted and threads must share, acquiring a pthread_mutex before allocating."),
        bullet("When an arena needs to grow, malloc calls mmap or brk — both system calls that trap into the kernel. This directly explains the elevated sys time observed in Q1."),
        bullet("Even when arena locks are not contended, malloc must walk a freelist or check bins on every call — this is non-deterministic latency that violates the constant-time promise of a ring buffer enqueue."),
        bullet("The combination means the queue is not actually lock-free: under sustained load, threads will serialise on the malloc arena mutex just as they would on a conventional mutex-protected queue."),
      ]),
      gap(),
      marksBand([
        { range: "4–5", label: "Full",    color: "green",
          desc: "Explains vtable pointer overhead and pointer chasing for Part A. For Part B, identifies arena mutex contention and mmap/brk system calls, and connects both directly to the sys time observation from Q1." },
        { range: "2–3", label: "Partial", color: "amber",
          desc: "Correctly handles one part. May mention 'malloc is slow' without explaining the kernel path, or may note the vtable pointer without explaining the pointer-chasing cache impact." },
        { range: "0–1", label: "Minimal", color: "red",
          desc: "States only that 'new is slow' or 'virtual functions have overhead' without mechanistic explanation." },
      ]),
      gap(), rule(),

      // ══════════════════════════════════════════════════════════════════════
      // Q6
      // ══════════════════════════════════════════════════════════════════════
      qHeader(6, "Proposing and justifying all three fixes", "7 marks"),
      gap(),

      ...answerBlock("Model Answer", [
        body("Flaw 1 — False sharing on the atomic index variables", { bold: true }),
        bullet("Flaw: head_ and tail_ occupy the same 64-byte cache line, so every write to one variable invalidates the other core's cached copy of both."),
        bullet("Fix: Declare each variable with alignas(64) (or alignas(std::hardware_destructive_interference_size)) to force them onto separate cache lines."),
        bullet("Mechanism: Once they are on separate lines, a consumer updating head_ does not touch the cache line containing tail_. The producer core's copy of tail_ stays in Shared or Modified state and never needs to be re-fetched from the interconnect. HITM events drop to near zero."),
        gap(),
        body("Flaw 2 — Implicit seq_cst memory ordering", { bold: true }),
        bullet("Flaw: Every atomic load, store, and CAS defaults to seq_cst, emitting unnecessary LOCK-prefixed instructions and draining the CPU store buffer on every operation."),
        bullet("Fix: Use explicit acquire/release ordering: relaxed or acquire on loads, release on stores and the success path of compare_exchange_weak."),
        bullet("Mechanism: Acquire/release creates a directed happens-before edge between producer and consumer without forcing a global ordering across all threads. On x86_64, acquire loads and release stores compile to ordinary mov instructions with no fence. Only the CAS itself retains a LOCK prefix, which is unavoidable but now appears only once per successful slot claim rather than on every single atomic access."),
        gap(),
        body("Flaw 3 — Dynamic allocation and virtual destructor on the hot path", { bold: true }),
        bullet("Flaw: Every enqueue calls new LogEntry(), which invokes glibc malloc under 4-thread contention, acquires arena locks, potentially calls mmap, and returns a pointer to a random heap address. The virtual destructor adds a vtable pointer to every object."),
        bullet("Fix: Remove the virtual destructor (make LogEntry a plain struct), replace LogEntry** storage_ with a pre-allocated LogEntry* storage_ (a flat array), and allocate it once in the constructor with new LogEntry[capacity]."),
        bullet("Mechanism: All entries now reside in contiguous memory. The CPU's hardware prefetcher can stride through them sequentially. There is no pointer chasing — the data is at a fixed, predictable offset from the base pointer. Zero heap allocations occur on the hot path, eliminating arena locks and kernel system calls entirely. sys time drops to near zero."),
        gap(),
        body("Bonus — Bitwise modulo (no marks):", { italic: true }),
        bullet("Constraining capacity to a power of 2 lets you replace current_tail % capacity_ with current_tail & (capacity_ - 1). The % operator compiles to divq (30–90 cycles); the bitwise AND compiles to a single and instruction (1 cycle)."),
      ]),
      gap(),
      marksBand([
        { range: "6–7", label: "Full",    color: "green",
          desc: "All three flaws correctly identified and fixed. Each fix is justified with the correct hardware mechanism: MESI/cache lines for flaw 1, store buffer/pipeline for flaw 2, pointer chasing/heap allocator for flaw 3. Terminology is accurate." },
        { range: "3–5", label: "Partial", color: "amber",
          desc: "Two of three flaws explained with correct mechanisms. The third may be identified but the mechanism is superficial (e.g. 'pre-allocation is faster' without explaining why)." },
        { range: "0–2", label: "Minimal", color: "red",
          desc: "Only one flaw addressed, or fixes are correct but all justifications are missing or incorrect." },
      ]),
      gap(), rule(),

      // ══════════════════════════════════════════════════════════════════════
      // Q7
      // ══════════════════════════════════════════════════════════════════════
      qHeader(7, "Interpreting perf stat counters after the fixes", "7 marks"),
      gap(),

      ...answerBlock("Model Answer", [
        body("Counter directions and explanations:", { bold: true }),
        gap(),
        q7Table(),
        gap(),
        body("Final paragraph — why IPC is not a proxy for throughput:", { bold: true }),
        bullet("In the optimised version, producers spend much of their time in a tight CAS retry loop or a PAUSE spin-wait. These loops execute almost no instructions — sometimes zero useful instructions per cycle — while waiting for the cache line ownership to resolve."),
        bullet("A low IPC in this context means 'the CPU is waiting for cache coherency', not 'the CPU is doing wasteful work'. The cycles spent waiting are genuinely necessary; the hardware has no choice but to stall."),
        bullet("Throughput rises because each successful operation completes in far fewer total cycles than before (no malloc, no false-sharing penalty, no store-buffer drain). Even if the CPU executes fewer instructions per clock during the waiting periods, the end-to-end time per item goes down."),
        bullet("The correct mental model: IPC measures instruction density, not work density. A CPU that does 1 useful instruction every 10 cycles (IPC 0.1) but where each instruction advances a queue item may outperform one that does 4 instructions every cycle (IPC 4) if most of those 4 instructions are malloc overhead."),
      ]),
      gap(),
      marksBand([
        { range: "6–7", label: "Full",    color: "green",
          desc: "All five counters have correct direction and a plausible mechanism. Final paragraph correctly explains that low IPC in a spin-heavy workload reflects waiting, not wasted work, and separates IPC from throughput clearly." },
        { range: "3–5", label: "Partial", color: "amber",
          desc: "Three or four counters correct. Final paragraph either missing or only partially correct — e.g. student says 'IPC should increase' without explaining why it might not." },
        { range: "0–2", label: "Minimal", color: "red",
          desc: "Fewer than three counters correct, or final paragraph contradicts Q3/Q4 findings." },
      ]),
      gap(),
      rule(),
      body("— End of Rubric —", { bold: true, italic: true }),
    ]
  }]
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync('assignment1_rubric.docx', buf);
  console.log('done');
});

