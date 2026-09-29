import { inflate } from "pako";

const decodeCompressedPlayerPayload = (compressedPayload) =>
  JSON.parse(inflate(compressedPayload, { toText: true }));

export { decodeCompressedPlayerPayload };
