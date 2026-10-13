// /lite/* — see edge/lite.js.
import { lite } from '../../edge/lite.js';

export function onRequest(context) {
  return lite(context.request, context);
}
