/* Header reader: copies inbound x-ctier-tier if present. The point of the fixture. */
var seen = context.getVariable('request.header.x-ctier-tier') || '';
context.setVariable('estate.sawTier', seen);
context.setVariable('request.header.X-Estate-Seen', '1');
