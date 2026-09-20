/* 1.5.0: no agent-supplied x-ctier-* header reaches the backend. */
var names = (context.getVariable('request.headers.names') || '') + '';
names = names.replace(/\[|\]/g, '');
var parts = names.split(',');
for (var i = 0; i < parts.length; i++) {
  var n = parts[i].replace(/^\s+|\s+$/g, '');
  if (!n) continue;
  var lower = n.toLowerCase();
  if (lower.indexOf('x-ctier-') === 0) {
    context.removeVariable('request.header.' + n);
  }
}
