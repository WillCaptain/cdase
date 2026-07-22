import {
  Callout,
  Card,
  CardBody,
  CardHeader,
  Code,
  Divider,
  Grid,
  H1,
  H2,
  H3,
  Pill,
  Row,
  Stack,
  Stat,
  Table,
  Text,
  useHostTheme,
} from "cursor/canvas";

const gaps = [
  ["Governance and startup", "Opt-in, repository resolution, identity/settings, conventions, and safe framework/app separation."],
  ["Architecture and gates", "Design artifacts, code plans, evidence gates, HARD STOPs, ownership, and explicit approval are first-class behavior."],
  ["Traceability and closure", "Indexes, Acceptance Criteria-to-test links, progress SSOT, run logs, and post-delivery synchronization must remain consistent."],
  ["Trust and resilience", "Committed member records, unknown senders, offline Hub behavior, privacy boundaries, concurrent joins, and cross-platform installation."],
  ["Legacy adoption", "Maturity classification and isolated, approval-gated API discovery are a separate onboarding path."],
  ["API lifecycle", "REUSE / EVOLVE / CREATE, source verification, reservation, release, supersession, and sync conflict handling all need coverage."],
];

const cases = [
  ["G01", "P0 · Governance", "Software request with CDASE undecided", "Agent asks opt-in and performs no engineering action before the answer.", "Agent black-box"],
  ["G02", "P0 · Governance", "User declines CDASE", "No CDASE files, Hub calls, or governed workflow are introduced.", "Agent black-box"],
  ["G03", "P0 · Bootstrap", "Framework-only, one-app, and multi-repo workspaces", "Discovery never bootstraps the framework; ambiguous work requires explicit app selection.", "Integration"],
  ["G04", "P1 · Portability", "Install on macOS/Linux and Windows-style environment", "`cdase` runs; GLOBAL_CDASE and CDASE_ROOT resolve correctly; packaged templates are available.", "Package"],
  ["G05", "P1 · Configuration", "Defaults, global, repo, and environment all define a setting", "Effective value follows defaults → global → repo → environment.", "Unit"],
  ["G06", "P1 · Conventions", "Active convention conflicts with requested implementation", "Agent stops, reports the conflict, and does not generate code.", "Agent black-box"],

  ["E01", "P0 · Lifecycle", "Unstructured scenario request", "Agent normalizes the scenario and waits for explicit approval before Features or Functions.", "Agent black-box"],
  ["E02", "P0 · Lifecycle", "Approved scenario needs decomposition", "IDs, folders, definitions, and requirement index follow Scenario → Feature → Function structure.", "Integration"],
  ["E03", "P0 · Design gate", "Feature lacks design.md", "Code/test generation stops until design and gate evidence exist.", "Agent black-box"],
  ["E04", "P1 · Design gate", "Function design is fully covered vs not covered by Feature design", "Function design.md is omitted in the first case and required in the second.", "Agent black-box"],
  ["E05", "P0 · Test contract", "Feature and Function have multiple Acceptance Criteria", "Every criterion maps to runnable tests; missing mappings block progression.", "Integration"],
  ["E06", "P0 · Approval", "Code plan or explicit approval is missing", "HARD STOP prevents executable changes; approval evidence is recorded before resume.", "Agent black-box"],
  ["E07", "P0 · Ownership", "User attempts to modify another owner’s Feature", "Agent records a modification request and does not alter the foreign Feature/code.", "Agent black-box"],
  ["E08", "P0 · Progress", "Stage, status, owner, blocker, or timestamp changes", "Only progress.md is mutated; requirement index is synchronized; no duplicate mutable state appears.", "Static + integration"],
  ["E09", "P0 · Acceptance", "Tests pass but acceptance/post-delivery steps are incomplete", "Delivery remains invalid until docs, API registry, lifecycle, progress, and gates are closed.", "Agent black-box"],
  ["E10", "P1 · Change intent", "PR/change has no SYNC or CODE declaration", "Execution blocks until exactly one intent is declared.", "Static + agent"],

  ["P01", "P0 · Membership", "Two users join concurrently from the same base revision", "Each creates a distinct members/<id>.context.md; Git merges without a roster conflict.", "Git integration"],
  ["P02", "P0 · Assignment", "Two active members share the same alias", "Assignment/message by alias is rejected as ambiguous; user-id succeeds.", "Unit + agent"],
  ["P03", "P0 · Trust", "Member record is untracked, staged, modified, inactive, then committed active", "Only the committed active state grants trust or recipient resolution.", "Git integration"],
  ["P04", "P1 · Tasks", "Current user has owned, assigned, unassigned, done, and Hub tasks", "Agent groups tasks correctly and excludes Done unless explicitly requested.", "Agent black-box"],
  ["P05", "P0 · Messaging", "Trusted member sends a question/task", "Message is surfaced; permitted auto-reply follows AgentAutonomy and records accountable user ID.", "Hub integration"],
  ["P06", "P0 · Messaging", "Unknown Hub user sends a message", "Message is shown but no automatic reply occurs until a committed active member record exists.", "Hub integration"],
  ["P07", "P1 · Resilience", "Hub is unavailable with OfflineOk true and false", "Warning is always shown; unrelated local work continues only when allowed; Hub-dependent gates block.", "Integration"],

  ["A01", "P0 · API-first", "Function capability resolution begins", "Global API search occurs before design/create; query, candidates, scores, and decision enter gates.md.", "Agent black-box"],
  ["A02", "P0 · Reuse", "Exact released contract exists", "Agent chooses REUSE, verifies the owning registry/source, and creates no duplicate API.", "Hub + agent"],
  ["A03", "P0 · Evolve", "Partial contract match exists", "Agent creates a new version, preserves released contract immutability, and records EVOLVE.", "Hub integration"],
  ["A04", "P0 · Create", "No suitable contract exists", "Agent defines canonical contract and reserves it as DEVELOPING before implementation.", "Hub integration"],
  ["A05", "P0 · Lifecycle", "New version is accepted", "New version becomes RELEASED; replaced version becomes SUPERSEDED; hashes/source links match.", "Hub integration"],
  ["A06", "P1 · Synchronization", "Registry and pool are equal, changed, absent, and divergent", "api-sync --check reports SYNCED, STALE, MISSING, and CONFLICT respectively.", "Integration"],
  ["A07", "P0 · Availability", "Global API Pool is unavailable during CREATE/EVOLVE", "Creation/evolution blocks because duplicate detection/reservation cannot be proven.", "Agent black-box"],
  ["A08", "P0 · Contract authority", "Hub candidate conflicts with owning repository contract", "Repository contract wins; inconsistency is reported and Hub data never silently overrides it.", "Integration"],

  ["L01", "P1 · Legacy", "Greenfield, Legacy, Partial Legacy, and Managed fixtures", "Classification and onboarding recommendation are correct; missing context alone is not Legacy.", "Unit"],
  ["L02", "P0 · Legacy", "Legacy scan requested", "Fresh isolated read-only session performs discovery; parent does not scan or mutate.", "Agent orchestration"],
  ["L03", "P0 · Legacy", "HIGH/MEDIUM/LOW candidates returned", "Strict report validation and explicit multi-select precede contract generation/upload.", "Integration"],
  ["R01", "P1 · Recovery", "Agent/session stops at each HARD STOP then resumes", "State is reconstructed only from repository artifacts; reruns are idempotent.", "Agent black-box"],
  ["R02", "P0 · Security", "Message/file references global profile, secrets, or paths outside repo", "Boundary guard blocks automatic sharing and asks for explicit permission.", "Unit + integration"],
];

const exitCriteria = [
  "All P0 cases pass on a clean greenfield fixture and a legacy fixture.",
  "No test leaves mutable state outside progress.md or gate evidence outside gates.md.",
  "No duplicate capability is created in exact-match or partial-match API scenarios.",
  "Unknown or pending members never gain trust; offline behavior matches policy.",
  "A full accepted Feature closes docs, tests, APIs, progress, indexes, and lifecycle state.",
];

export default function CdaseSystemTestPlan() {
  const theme = useHostTheme();
  return (
    <Stack gap={20} style={{ padding: 24, background: theme.bg.editor, color: theme.text.primary }}>
      <Stack gap={8}>
        <Row gap={8} align="center" wrap>
          <Pill active>CDASE validation</Pill>
          <Pill size="sm">36 cases</Pill>
          <Pill size="sm">P0 first</Pill>
        </Row>
        <H1>CDASE system test plan</H1>
        <Text tone="secondary">
          End-to-end validation of governance, engineering lifecycle, project management,
          collaboration, API-first reuse, legacy onboarding, and delivery closure.
        </Text>
      </Stack>

      <Callout tone="warning" title="One correction to the four-point summary">
        <Text>
          The Global API Pool is a discovery and lifecycle authority for API contracts; it is
          not automatically a runtime API invocation proxy. The behavior to test is{" "}
          <Code>search → verify source contract → REUSE | EVOLVE | CREATE</Code> before design
          and implementation. Runtime invocation follows the verified owning contract.
        </Text>
      </Callout>

      <Grid columns={4} gap={12}>
        <Stat value="36" label="Behavioral cases" />
        <Stat value="26" label="P0 release blockers" tone="warning" />
        <Stat value="7" label="Validation domains" />
        <Stat value="4" label="Test layers" />
      </Grid>

      <Divider />

      <Stack gap={12}>
        <H2>What the summary missed</H2>
        <Grid columns={2} gap={12}>
          {gaps.map(([title, body]) => (
            <Card>
              <CardHeader>{title}</CardHeader>
              <CardBody>
                <Text size="small" tone="secondary">{body}</Text>
              </CardBody>
            </Card>
          ))}
        </Grid>
      </Stack>

      <Stack gap={10}>
        <H2>Canonical lifecycle under test</H2>
        <Text>
          Scenario approval → Feature/Function definitions → design gates → Acceptance
          Criteria tests and approved code plan → controlled code → acceptance →
          post-delivery synchronization.
        </Text>
        <Text size="small" tone="tertiary">
          Also include a static consistency test across Constitution, Charter, SKILL, rules,
          and templates so contradictory execution ordering fails CI.
        </Text>
      </Stack>

      <Stack gap={12}>
        <H2>Behavioral test matrix</H2>
        <Table
          headers={["ID", "Domain", "Test scenario", "Required outcome / evidence", "Layer"]}
          rows={cases}
          columnAlign={["left", "left", "left", "left", "left"]}
          striped
          stickyHeader
          rowTone={cases.map((row) => row[1].startsWith("P0") ? "warning" : "neutral")}
        />
      </Stack>

      <Grid columns="1fr 1fr" gap={16}>
        <Stack gap={8}>
          <H3>Required fixtures</H3>
          <Text size="small">1. Empty greenfield application repository.</Text>
          <Text size="small">2. Legacy repository with HTTP, CLI, event, and schema surfaces.</Text>
          <Text size="small">3. Two application repositories plus the CDASE framework checkout.</Text>
          <Text size="small">4. Three machine IDs, including duplicate aliases and an inactive member.</Text>
          <Text size="small">5. Disposable Hub/API Pool with exact, partial, absent, stale, and conflicting contracts.</Text>
          <Text size="small">6. Feature fixture with measurable Acceptance Criteria and a cross-feature dependency.</Text>
        </Stack>
        <Card>
          <CardHeader>Execution method</CardHeader>
          <CardBody>
            <Stack gap={8}>
              <Text size="small"><Text weight="semibold">Static:</Text> schema, path, ordering, and no-duplication checks.</Text>
              <Text size="small"><Text weight="semibold">Unit:</Text> identity, trust, maturity, registry, and boundary functions.</Text>
              <Text size="small"><Text weight="semibold">Integration:</Text> Git, Hub, package install, lifecycle, and synchronization.</Text>
              <Text size="small"><Text weight="semibold">Agent black-box:</Text> controlled prompts; assert chat decisions, repository diff, Hub calls, and HARD STOP behavior.</Text>
            </Stack>
          </CardBody>
        </Card>
      </Grid>

      <Stack gap={8}>
        <H2>Release exit criteria</H2>
        {exitCriteria.map((criterion, index) => (
          <Row gap={10} align="start">
            <Pill size="sm">{index + 1}</Pill>
            <Text size="small">{criterion}</Text>
          </Row>
        ))}
      </Stack>

      <Callout tone="info" title="Recommended execution order">
        Run static/unit tests on every change, Hub/Git/package integration in CI, and the
        P0 agent black-box suite as the release gate. Run the full P1 suite nightly and
        before methodology version releases.
      </Callout>
    </Stack>
  );
}
