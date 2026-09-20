/* Mint the join key on the forwarding path. */
var cid = context.getVariable('messageid') || ('apigee-' + Date.now());
function _ctierIso(d) {
  function p(n) { return n < 10 ? '0' + n : String(n); }
  return d.getUTCFullYear() + '-' + p(d.getUTCMonth() + 1) + '-' + p(d.getUTCDate())
    + 'T' + p(d.getUTCHours()) + ':' + p(d.getUTCMinutes()) + ':' + p(d.getUTCSeconds()) + 'Z';
}
var agent = context.getVariable('request.header.x-agent-id') || 'unknown';
var task = context.getVariable('request.header.x-task-id');
var rec = {
  ctierSchema: 'decision-record/0.2.0',
  type: 'decision',
  id: String(cid),
  timestamp: _ctierIso(new Date()),
  operationAnchor: context.getVariable('ctier.operation') || 'undeclared',
  agentId: agent,
  correlationScope: task || agent,
  correlationId: String(cid),
  declaredTier: parseInt(context.getVariable('ctier.tier'), 10) || 4,
  appliedTier: parseInt(context.getVariable('ctier.tier'), 10) || 4,
  escalationReason: 'none',
  disposition: 'execute',
  idempotencyKey: String(cid),
  deploymentDigest: context.getVariable('ctier.deployment')
};
var blob = JSON.stringify(rec);
print('[ctier-decision] ' + blob);
context.setVariable('ctier.record.json', blob);
context.setVariable('request.header.x-ctier-correlation-id', cid);
