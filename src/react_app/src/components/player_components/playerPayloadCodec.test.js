import { deflate } from "pako";
import { decodeCompressedPlayerPayload } from "./playerPayloadCodec";

describe("decodeCompressedPlayerPayload", () => {
  it("decodes the binary WebSocket payload as UTF-8 JSON", () => {
    const payload = {
      player_data: [{ splashtag: "イカ#1234" }],
      aggregated_data: {
        weapon_counts: [],
        weapon_winrate: [],
        season_results: [],
        aggregate_season_data: [],
        latest_data: [],
      },
    };
    const compressed = deflate(JSON.stringify(payload));
    const arrayBuffer = compressed.buffer.slice(
      compressed.byteOffset,
      compressed.byteOffset + compressed.byteLength
    );

    expect(decodeCompressedPlayerPayload(arrayBuffer)).toEqual(payload);
  });
});
