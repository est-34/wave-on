const {test} = require('node:test');
const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const vm = require('node:vm');

test('page navigation restores deep links, history, focus and retained input', () => {
  const pages = ['task', 'context', 'memory'].map(name => ({
    id: `workspace-${name}`, hidden: false, input: '수정 중인 값',
    focus(options) { this.focusOptions = options; },
  }));
  const links = pages.map(page => ({
    hash: `#${page.id}`,
    setAttribute(key, value) { this[key] = value; },
    removeAttribute(key) { delete this[key]; },
  }));
  const nodes = Object.fromEntries(pages.map(page => [page.id, page]));
  for (const id of ['pageTitle', 'pageDescription', 'taskContext']) nodes[id] = {};
  let onHashChange;
  let scrolls = 0;
  const window = {
    location: {hash: '#workspace-memory'},
    addEventListener(event, callback) { assert.equal(event, 'hashchange'); onHashChange = callback; },
    scrollTo(x, y) { assert.equal(x, 0); assert.equal(y, 0); scrolls++; },
  };
  vm.runInNewContext(readFileSync(`${__dirname}/../js/navigation.js`, 'utf8'), {
    window, document: {
      querySelectorAll: selector => selector === '.workspace-page' ? pages : links,
      getElementById: id => nodes[id],
    },
  });
  const current = index => {
    assert.deepEqual(links.filter(link => link['aria-current']), [links[index]]);
    assert.equal(links[index]['aria-current'], 'page');
    assert.deepEqual(pages.filter(page => !page.hidden), [pages[index]]);
  };
  current(2);
  assert.equal(nodes.pageTitle.textContent, '학습한 기억');
  assert.equal(nodes.taskContext.hidden, true);
  assert.equal(pages[2].focusOptions, undefined);
  window.location.hash = '#workspace-context';
  onHashChange({type: 'hashchange'});
  current(1);
  assert.equal(pages[1].focusOptions.preventScroll, true);
  assert.equal(nodes.pageTitle.textContent, '활동 맥락');
  for (const hash of ['', '#unknown', '#workspace-task']) {
    window.location.hash = hash;
    onHashChange({type: 'hashchange'});
    current(0);
    assert.equal(nodes.taskContext.hidden, false);
  }
  assert.equal(pages[2].input, '수정 중인 값');
  assert.equal(scrolls, 5);
});
