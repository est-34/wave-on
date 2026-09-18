const pageCopy = {
  'workspace-task': ['제스처 학습', '몸짓과 행동을 연결하고, 새로운 패턴을 승인합니다.'],
  'workspace-context': ['활동 맥락', '현재 활동을 선택하고, 몸짓의 해석과 개인정보 보호 정책을 확인합니다.'],
  'workspace-memory': ['학습한 기억', '승인한 연결의 신뢰도와 학습·실행 기록을 확인합니다.'],
};

function updateNavigation(event) {
  const links = document.querySelectorAll('.floating-navigation a');
  const selected = Array.from(links).find(link => link.hash === window.location.hash) || links[0];
  for (const link of links) {
    if (link === selected) link.setAttribute('aria-current', 'page');
    else link.removeAttribute('aria-current');
  }
  const pageId = selected.hash.slice(1);
  for (const page of document.querySelectorAll('.workspace-page')) {
    page.hidden = page.id !== pageId;
  }
  const [title, description] = pageCopy[pageId];
  document.getElementById('pageTitle').textContent = title;
  document.getElementById('pageDescription').textContent = description;
  document.getElementById('taskContext').hidden = pageId !== 'workspace-task';
  document.title = `${title} · SilentOrchestra 2.0`;
  if (event) document.getElementById(pageId).focus({preventScroll: true});
  window.scrollTo(0, 0);
}
window.addEventListener('hashchange', updateNavigation);
updateNavigation();
