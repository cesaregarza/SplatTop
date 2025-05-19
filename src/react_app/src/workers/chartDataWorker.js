import { inflate } from 'pako';

self.onmessage = (e) => {
  const payload = e.data;
  if (payload instanceof Blob) {
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const text = inflate(new Uint8Array(reader.result), { to: 'string' });
        self.postMessage(JSON.parse(text));
      } catch (err) {
        self.postMessage({ error: err.message });
      }
    };
    reader.readAsArrayBuffer(payload);
  } else {
    try {
      const data = typeof payload === 'string' ? JSON.parse(payload) : payload;
      self.postMessage(data);
    } catch (err) {
      self.postMessage({ error: err.message });
    }
  }
};
