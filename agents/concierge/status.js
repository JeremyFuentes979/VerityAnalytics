#!/usr/bin/env node
/**
 * concierge/status.js
 * 
 * Status Generator — queries a session's artifact directory and returns
 * a structured status object the frontend can consume.
 * 
 * Usage (CLI):
 *   node agents/concierge/status.js <sessionId>
 * 
 * Usage (import):
 *   const { getStatus } = require('./agents/concierge/status.js');
 *   const status = await getStatus('session-uuid-here');
 * 
 * Returns: { workflow, summary, session } or null if session not found.
 */

const fs = require('node:fs/promises');
const path = require('node:path');
const TEMPLATES = require('./templates.json');

// VERITY_SESSIONS_DIR overrides; default is <repo>/sessions (this file lives in <repo>/agents/concierge).
const SESSIONS_DIR = process.env.VERITY_SESSIONS_DIR || path.resolve(__dirname, '..', '..', 'sessions');

/**
 * Ordered workflow stages. Each maps to a specific artifact file and agent.
 */
const WORKFLOW_STAGES = [
  {
    key: 'profile',
    artifactFile: 'profile.json',
    agent: 'Researcher',
    label: 'Data Profiling',
    emoji: '🔍',
    inProgressTemplate: 'profiling',
    doneTemplate: 'researcher_done',
  },
  {
    key: 'analysis',
    artifactFile: 'analysis.json',
    agent: 'Analyst',
    label: 'Pattern Analysis',
    emoji: '📊',
    inProgressTemplate: 'analyst_working',
    doneTemplate: 'analyst_done',
  },
  {
    key: 'auditTrail',
    artifactFile: 'audit_trail.json',
    agent: 'Auditor',
    label: 'Validation & Cleaning',
    emoji: '✅',
    inProgressTemplate: 'auditor_working',
    doneTemplate: 'auditor_done',
  },
  {
    key: 'decisionMemo',
    artifactFile: 'decision_memo.json',
    agent: 'Manager',
    label: 'Synthesis & Decision Memo',
    emoji: '📋',
    inProgressTemplate: 'manager_working',
    doneTemplate: 'manager_done',
  },
  {
    key: 'workbook',
    artifactFile: 'final_workbook.xlsx',
    agent: 'Manager',
    label: 'Excel Workbook',
    emoji: '📑',
    inProgressTemplate: 'manager_working',
    doneTemplate: 'workbook_ready',
  },
];

/**
 * Get the status of a session by checking which artifact files exist.
 * @param {string} sessionId
 * @returns {Promise<object|null>}
 */
async function getStatus(sessionId) {
  const sessionPath = path.join(SESSIONS_DIR, sessionId);

  // Try to read session metadata
  let session = null;
  try {
    const raw = await fs.readFile(path.join(sessionPath, 'session.json'), 'utf8');
    session = JSON.parse(raw);
  } catch {
    return null; // session not found
  }

  // Check each stage
  const stages = [];
  let allComplete = true;
  let lastCompleteIdx = -1;

  for (let i = 0; i < WORKFLOW_STAGES.length; i++) {
    const stage = WORKFLOW_STAGES[i];
    const artifactPath = path.join(sessionPath, stage.artifactFile);
    let isDone = false;

    try {
      await fs.access(artifactPath);
      isDone = true;
      lastCompleteIdx = i;
    } catch {
      allComplete = false;
    }

    // Determine the message to show
    let progressMessage = null;
    if (isDone) {
      const tpl = TEMPLATES.progress[stage.doneTemplate];
      progressMessage = {
        title: tpl?.title || `${stage.agent} Complete`,
        message: tpl?.message || `${stage.agent} has finished.`,
        detail: tpl?.detail || '',
        emoji: tpl?.emoji || stage.emoji,
        cta: tpl?.cta || null,
      };
    } else {
      // Show "in progress" for the current active stage (first incomplete),
      // "waiting" for future stages
      const isActive = i === lastCompleteIdx + 1;
      if (isActive) {
        const tpl = TEMPLATES.progress[stage.inProgressTemplate];
        progressMessage = {
          title: tpl?.title || `${stage.agent} Working`,
          message: tpl?.message || `${stage.agent} is working on ${stage.label.toLowerCase()}...`,
          detail: tpl?.detail || '',
          emoji: tpl?.emoji || stage.emoji,
          cta: tpl?.cta || null,
        };
      } else {
        // Future stages show generic waiting message
        progressMessage = {
          title: `${stage.agent} — ${stage.label}`,
          message: `Waiting for previous step to complete.`,
          detail: '',
          emoji: stage.emoji,
          cta: null,
        };
      }
    }

    stages.push({
      key: stage.key,
      agent: stage.agent,
      label: stage.label,
      isDone,
      isActive: i === lastCompleteIdx + 1 && !isDone,
      progressMessage,
    });
  }

  // Determine overall status
  let status;
  let summaryMessage;
  if (allComplete) {
    status = 'complete';
    summaryMessage = {
      badge: TEMPLATES.result_presentation.all_complete.badge,
      headline: TEMPLATES.result_presentation.all_complete.headline,
      subheadline: TEMPLATES.result_presentation.all_complete.subheadline,
    };
  } else if (stages[0]?.isDone) {
    status = 'analysis_running';
    summaryMessage = {
      badge: TEMPLATES.result_presentation.in_progress.badge,
      headline: TEMPLATES.result_presentation.in_progress.headline,
      subheadline: TEMPLATES.result_presentation.in_progress.subheadline,
    };
  } else if (session.status === 'hired' || session.status === 'paid' || session.status === 'queued') {
    status = 'analysis_started';
    summaryMessage = {
      badge: 'Analysis Started',
      headline: 'The Firm Has Been Hired',
      subheadline: TEMPLATES.progress.analysis_started.detail,
    };
  } else {
    status = 'preview_ready';
    const previewTpl = TEMPLATES.progress.preview_ready;
    summaryMessage = {
      badge: 'Preview Ready',
      headline: previewTpl.title,
      subheadline: previewTpl.message,
    };
  }

  return {
    sessionId,
    session,
    status,
    allComplete,
    stages,
    summary: summaryMessage,
    canDownload: allComplete,
    currentStage: stages.find((s) => s.isActive)?.key || null,
  };
}

/**
 * Get a short current-stage message suitable for showing in a status bar or
 * during upload processing.
 * @param {string} sessionId
 * @returns {Promise<object|null>}
 */
async function getCurrentMessage(sessionId) {
  const full = await getStatus(sessionId);
  if (!full) return null;

  // Find the active stage (first not done)
  const activeStage = full.stages.find((s) => s.isActive);
  if (activeStage) {
    return {
      type: 'progress',
      ...activeStage.progressMessage,
      stage: activeStage.key,
    };
  }

  // All done
  if (full.allComplete) {
    return {
      type: 'complete',
      title: TEMPLATES.progress.workbook_ready.title,
      message: TEMPLATES.progress.workbook_ready.message,
      detail: TEMPLATES.progress.workbook_ready.detail,
      emoji: TEMPLATES.progress.workbook_ready.emoji,
      cta: TEMPLATES.progress.workbook_ready.cta,
    };
  }

  return null;
}

// CLI mode
if (require.main === module) {
  const sessionId = process.argv[2];
  if (!sessionId) {
    console.error('Usage: node status.js <sessionId>');
    process.exit(1);
  }
  getStatus(sessionId)
    .then((result) => {
      if (!result) {
        console.log(JSON.stringify({ error: 'Session not found', sessionId }));
        process.exit(0);
      }
      console.log(JSON.stringify(result, null, 2));
    })
    .catch((err) => {
      console.error('Error:', err.message);
      process.exit(1);
    });
}

module.exports = { getStatus, getCurrentMessage, WORKFLOW_STAGES };