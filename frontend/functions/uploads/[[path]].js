// Report photos, cached at the edge for as long as the API allows.
import { handle } from '../../edge/gateway.js';

export function onRequest(context) {
  return handle(context.request, context);
}
