// n8n Code node: turn the /evaluate response into a Slack Block Kit message.
// Source of the "Build Slack message" node in recruiting_intake.json.
const r = $input.first().json;
const channel = $env.SLACK_CHANNEL_ID;
const jobSlug = $('Application webhook').first().json.body.job_slug;

const RECOMMENDATION = {
  advance: ':large_green_circle: Weiter',
  review: ':large_yellow_circle: Prüfen',
  reject_suggested: ':red_circle: Absage vorgeschlagen',
};
const bullets = (items) => (items && items.length ? items.map((i) => `• ${i}`).join('\n') : '–');

// /evaluate failed before an evaluation was stored (e.g. unreadable PDF).
if (!r.evaluation_id) {
  const reason = r.detail || (r.error && r.error.message) || 'unbekannter Fehler';
  return [{ json: {
    response: { status: 'failed', detail: reason },
    slack: { channel, text: `Bewerbung für ${jobSlug} konnte nicht verarbeitet werden: ${reason}` },
  } }];
}

const blocks = [
  { type: 'header', text: { type: 'plain_text', text: `Neue Bewerbung: ${r.job_title}` } },
];

if (r.status === 'ok') {
  const e = r.evaluation;
  blocks.push(
    { type: 'section', fields: [
      { type: 'mrkdwn', text: `*Score*\n${e.score} / 100` },
      { type: 'mrkdwn', text: `*KI-Empfehlung*\n${RECOMMENDATION[e.recommendation]}` },
    ] },
    { type: 'section', text: { type: 'mrkdwn', text: `*Stärken*\n${bullets(e.strengths)}` } },
    { type: 'section', text: { type: 'mrkdwn', text: `*Lücken*\n${bullets(e.gaps)}` } },
    { type: 'section', text: { type: 'mrkdwn', text: `*Begründung*\n${e.reasoning}` } },
  );
} else {
  blocks.push({ type: 'section', text: { type: 'mrkdwn',
    text: `:warning: *KI-Bewertung fehlgeschlagen* (${r.status}). Bitte den Lebenslauf manuell prüfen.` } });
}

blocks.push(
  { type: 'context', elements: [{ type: 'mrkdwn',
    text: `Die KI gibt nur eine Empfehlung – die Entscheidung triffst du. ` +
          `Modell ${r.model}, Prompt ${r.prompt_version}, Bewerbung \`${r.application_id}\`` }] },
  { type: 'actions', elements: [
    { type: 'button', style: 'primary', action_id: 'decision_advance', value: r.evaluation_id,
      text: { type: 'plain_text', text: 'Weiter' } },
    { type: 'button', style: 'danger', action_id: 'decision_reject', value: r.evaluation_id,
      text: { type: 'plain_text', text: 'Absage' },
      confirm: {
        title: { type: 'plain_text', text: 'Absage bestätigen' },
        text: { type: 'mrkdwn', text: 'Diese Entscheidung wird im Audit-Log gespeichert.' },
        confirm: { type: 'plain_text', text: 'Absage' },
        deny: { type: 'plain_text', text: 'Abbrechen' },
      } },
  ] },
);

const score = r.status === 'ok' ? ` (Score ${r.evaluation.score})` : '';
return [{ json: {
  response: { status: r.status, application_id: r.application_id, evaluation_id: r.evaluation_id },
  slack: { channel, text: `Neue Bewerbung: ${r.job_title}${score}`, blocks },
} }];
