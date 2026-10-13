// Every /api/* request: see edge/gateway.js.
import { handle } from '../../edge/gateway.js';

export function onRequest(context) {
  return handle(context.request, context);
}
