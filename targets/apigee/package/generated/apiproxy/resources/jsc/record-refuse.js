/* Decision on a refuse path. Trace print is not kit_records. */
var cid = context.getVariable('messageid') || ('apigee-' + Date.now());
function _ctierIso(d) {
  function p(n) { return n < 10 ? '0' + n : String(n); }
  return d.getUTCFullYear() + '-' + p(d.getUTCMonth() + 1) + '-' + p(d.getUTCDate())
    + 'T' + p(d.getUTCHours()) + ':' + p(d.getUTCMinutes()) + ':' + p(d.getUTCSeconds()) + 'Z';
}
var agent = context.getVariable('request.header.x-agent-id') || 'unknown';
var task = context.getVariable('request.header.x-task-id');
var tier = parseInt(context.getVariable('ctier.tier'), 10) || 4;
var excluded = context.getVariable('ctier.excluded') === 'true';
var declared = context.getVariable('ctier.declared') === 'true';
var op = context.getVariable('ctier.operation') || 'undeclared';
var disposition;
var reason;
var applied = tier;
if (excluded || tier === 3) {
  disposition = 'refuse-provisioning';
  reason = excluded ? 'excluded' : 'class-3-without-persist';
} else {
  disposition = 'refuse-and-suspend';
  applied = 4;
  reason = declared ? 'classified-refuse' : 'undeclared-operation';
}
var rec = {
  ctierSchema: 'decision-record/0.2.0',
  type: 'decision',
  id: String(cid),
  timestamp: _ctierIso(new Date()),
  operationAnchor: op,
  agentId: agent,
  correlationScope: task || agent,
  correlationId: String(cid),
  declaredTier: declared ? tier : 4,
  appliedTier: applied,
  escalationReason: reason,
  disposition: disposition,
  idempotencyKey: String(cid),
  deploymentDigest: context.getVariable('ctier.deployment')
};
var blob = JSON.stringify(rec);
print('[ctier-decision] ' + blob);
context.setVariable('ctier.record.json', blob);
