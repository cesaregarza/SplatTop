// jest-dom adds custom jest matchers for asserting on DOM nodes.
// allows you to do things like:
// expect(element).toHaveTextContent(/react/i)
// learn more: https://github.com/testing-library/jest-dom
import '@testing-library/jest-dom';

const { TextDecoder, TextEncoder } = require("node:util");
const {
  ReadableStream,
  TransformStream,
  WritableStream,
} = require("node:stream/web");
const { MessageChannel, MessagePort } = require("node:worker_threads");
const originalMessageChannel = globalThis.MessageChannel;
const originalMessagePort = globalThis.MessagePort;

Object.assign(globalThis, {
  ReadableStream,
  MessageChannel,
  MessagePort,
  TextDecoder,
  TextEncoder,
  TransformStream,
  WritableStream,
});

const { Headers, Request, Response } = require("undici");

Object.assign(globalThis, { Headers, Request, Response });

// Undici needs these Node globals while it initializes, but leaving them in
// jsdom makes React's scheduler retain a worker-thread port after tests finish.
if (originalMessageChannel === undefined) delete globalThis.MessageChannel;
else globalThis.MessageChannel = originalMessageChannel;
if (originalMessagePort === undefined) delete globalThis.MessagePort;
else globalThis.MessagePort = originalMessagePort;

globalThis.CSS ??= {};
globalThis.CSS.supports ??= () => false;
