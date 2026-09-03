import "@testing-library/jest-dom/vitest";

// jsdom doesn't implement Element.scrollTo — stub it so components that call
// it (e.g. ChatWindow auto-scrolling to the latest message) don't throw when
// mounted in tests. No assertions rely on actual scroll behavior.
if (!Element.prototype.scrollTo) {
  Element.prototype.scrollTo = () => {};
}
