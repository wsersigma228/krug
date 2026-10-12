import re,sys
src=open("home.html").read()
header=re.search(r"<header>.*?</header>",src,re.S).group(0)
dock=re.search(r'<nav class="dock".*?</nav>',src,re.S).group(0)
head=src[:src.index("<body>")]
def page(name,title,active,body,c="project",mono=""):
    h=head.replace(re.search(r"<title>.*?</title>",head).group(0),f"<title>Krug — {title}</title>")
    hd=header.replace(' aria-current="page"','')
    hd=hd.replace(f'</svg>{active}</a>',f'</svg>{active}</a>').replace(f'<a href="#"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">',f'<a href="#"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">')
    # mark active nav by label
    hd=re.sub(r'<a href="#">(<svg[^>]*>(?:(?!</a>).)*?</svg>'+re.escape(active)+r')</a>',r'<a aria-current="page" href="#">\1</a>',hd,count=1,flags=re.S)
    m=re.search(r'--c:var\(--c-(\w+)\)',body); c=m.group(1) if m else c
    em=re.search(r'class="emblem[^"]*">([^<]+)<',body); mono=em.group(1)[0] if em else mono
    body=body.replace('class="page-head"',f'class="page-head" data-mono="{mono}"',1)
    html=h+f'<body style="--c:var(--c-{c})" data-type="{c}">\n'+hd+"\n"+body+"\n"+dock+'\n<script>{{const q=new URLSearchParams(location.search);document.documentElement.dataset.theme=q.get("theme")||"light";document.documentElement.dataset.font=q.get("font")||"c"}}</script>\n<script src="proto-en.js"></script>\n</body>\n</html>\n'
    open(name,"w").write(html)
ROLE_IC='<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg>'
SAVE='<button class="btn line icon" aria-label="Сохранить"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M6 4h12v17l-6-4-6 4z"/></svg></button>'
SHARE='<button class="btn line icon" aria-label="Поделиться"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 12v7h16v-7M12 3v12M7 8l5-5 5 5"/></svg></button>'

# ---------- PROJECT ----------
page("project.html","Бродячий маяк","Поиск",f'''
<section class="page-head" style="--c:var(--c-project)"><div class="wrap">
  <div class="crumbs"><a href="#">Поиск</a><span>/</span><a href="#">Проекты</a><span>/</span><span>Бродячий маяк</span></div>
  <div class="head-grid">
    <div class="emblem">Б</div>
    <div><h1 class="page-title">Бродячий маяк</h1><p class="page-sub">Кооперативная головоломка о свете и тенях для двух игроков.</p>
      <div class="head-meta"><span class="kind-l">Проект Круга</span><span>Владелец <b>Алексей Котов</b></span><span><b>5</b> участников</span><span>обновлён <b>2 дня назад</b></span><span><b>12</b> сохранений</span></div></div>
    <div class="head-actions">{SAVE}{SHARE}<button class="btn line">Интересно</button><a class="btn hl" href="#roles">Открытые роли · 1</a></div>
  </div>
</div></section>
<div class="subnav"><div class="wrap"><nav><a aria-current="page" href="#">Обзор</a><a href="#">Роли<span class="num">2</span></a><a href="#">Обновления<span class="num">6</span></a><a href="#">Участники<span class="num">5</span></a></nav></div></div>
<div class="wrap detail">
  <main>
    <section class="box"><div class="box-h"><h2>О проекте</h2></div><div class="box-b prose">
      <p>Двое игроков управляют светом и тенью: один освещает путь, второй проходит по теням, которые свет отбрасывает. Уровни строятся вокруг того, что видно только одному из двоих.</p>
      <p>Демо из 6 уровней готово, хотим довести до 20 уровней и выпустить в Steam весной. Работаем по вечерам, созвон раз в неделю.</p>
      <div class="tags" style="margin-top:1rem"><span class="tag">Unity</span><span class="tag">co-op</span><span class="tag">головоломка</span><span class="tag">левел-дизайн</span></div>
    </div></section>
    <section class="box" id="roles"><div class="box-h"><h2>Открытые роли</h2><a href="#">Все роли</a></div>
      <div class="role"><h3>Левел-дизайнер</h3><p>Придумывать и собирать уровни в Unity по готовым механикам, тестировать с командой.</p><div class="meta"><span>5–8 часов в неделю</span><span>UTC+2…+5</span><span>опыт не обязателен</span></div><div class="act"><button class="btn soft">Откликнуться</button></div></div>
      <div class="role closed"><h3>Композитор</h3><p>Набор закрыт — роль занята.</p><div class="meta"><span>закрыта 3 окт</span></div><div class="act"><span class="status wait">закрыта</span></div></div>
    </section>
    <section class="box"><div class="box-h"><h2>Обновления</h2><a href="#">Все · 6</a></div>
      <article class="update"><div class="by"><span class="av" style="--c:var(--c-project)">АК</span>Алексей Котов · 2 дня назад</div><h3>Шестой уровень и новый свет</h3><p>Переделали источник света: теперь тени мягкие и читаются лучше. Шестой уровень собран, ждём тестеров.</p><div class="acts"><span>♡ 14</span><span>Комментарии · 3</span></div></article>
      <article class="update"><div class="by"><span class="av" style="--c:var(--c-team)">ЛМ</span>Лиза Маркова · 9 дней назад</div><h3>Сценарий первых трёх глав</h3><p>Короткие сцены между уровнями без текста — только пантомима и звук.</p><div class="acts"><span>♡ 9</span><span>Комментарии · 1</span></div></article>
    </section>
  </main>
  <aside class="side-stack">
    <section class="cta-box"><h2>Хотите участвовать?</h2><p>Откликнитесь на роль — владелец ответит, контакты откроются после принятия.</p><button class="btn hl">Откликнуться на роль</button></section>
    <section class="box"><div class="box-h"><h2>Детали</h2></div><div class="box-b"><dl class="facts"><dt>Формат</dt><dd>онлайн</dd><dt>Язык</dt><dd>русский</dd><dt>Нагрузка</dt><dd>вечера, 5–8 ч/нед</dd><dt>Стадия</dt><dd>демо готово</dd><dt>Создан</dt><dd>12 авг 2026</dd></dl></div></section>
    <section class="box"><div class="box-h"><h2>Участники</h2><a href="#">Все · 5</a></div><div class="people">
      <div class="person"><span class="av" style="--c:var(--c-project)">АК</span><div><b>Алексей Котов</b><span>владелец · Unity</span></div></div>
      <div class="person"><span class="av" style="--c:var(--c-team)">ЛМ</span><div><b>Лиза Маркова</b><span>сценарий</span></div></div>
      <div class="person"><span class="av" style="--c:var(--c-community)">ДР</span><div><b>Дима Рябов</b><span>2D-арт</span></div></div>
    </div></section>
  </aside>
</div>''')

# ---------- EVENT ----------
page("event.html","Осенний пиксель-джем","События",f'''
<section class="page-head" style="--c:var(--c-event)"><div class="wrap">
  <div class="crumbs"><a href="#">События</a><span>/</span><span>Осенний пиксель-джем</span></div>
  <div class="head-grid">
    <div class="emblem">О</div>
    <div><h1 class="page-title">Осенний пиксель-джем</h1><p class="page-sub">72 часа на пиксельную игру по теме, которую объявят на старте.</p>
      <div class="head-meta"><span class="kind-l">Game jam</span><span><b>16–19 октября</b></span><span>онлайн</span><span><b>41</b> участник</span><span><b>7</b> команд ищут людей</span></div></div>
    <div class="head-actions">{SAVE}{SHARE}<button class="btn line">Участвую</button><a class="btn hl" href="#">Найти команду</a></div>
  </div>
  <div class="head-band">
    <div class="tile"><div class="row"><span class="tag-s soon">регистрация</span><span class="t-kind">до 16 окт, 18:00 МСК</span></div><div class="big-clock" aria-label="До старта 3 дня 14 часов 20 минут"><div><b>03</b><span>дня</span></div><div><b>14</b><span>часов</span></div><div><b>20</b><span>минут</span></div></div></div>
    <div class="tile"><div class="row"><span class="t-kind">Сейчас на джеме</span></div><h3>7 команд ищут людей</h3><span class="t-kind">чаще всего ищут: 2D-арт, звук, программиста</span></div>
  </div>
</div></section>
<div class="subnav"><div class="wrap"><nav><a aria-current="page" href="#">Обзор</a><a href="#">Команды<span class="num">7</span></a><a href="#">Участники<span class="num">41</span></a><a href="#">Проекты<span class="num">0</span></a></nav></div></div>
<div class="wrap detail">
  <main>
    <section class="box"><div class="box-h"><h2>Этапы</h2></div><div class="box-b"><div class="phases">
      <div class="ph current"><b>Регистрация</b><span>до 16 окт, 18:00</span><i class="bar p-reg"></i></div>
      <div class="ph"><b>Джем · 72 часа</b><span>16 окт 18:00 — 19 окт 18:00</span><i class="bar p-run"></i></div>
      <div class="ph"><b>Голосование</b><span>19–26 окт</span><i class="bar p-vote"></i></div>
    </div></div></section>
    <section class="box"><div class="box-h"><h2>Команды ищут людей</h2><a href="#">Все · 7</a></div>
      <div class="role"><h3>Тихая станция</h3><p>Нарративный хоррор на Godot. Есть программист и сценарист.</p><div class="meta"><span>ищут: 2D-художник, звук</span><span>2 из 4 мест</span></div><div class="act"><button class="btn soft">Откликнуться</button></div></div>
      <div class="role"><h3>Пиксельные пчёлы</h3><p>Аркада про улей, нужен человек на музыку и звук.</p><div class="meta"><span>ищут: звук</span><span>3 из 4 мест</span></div><div class="act"><button class="btn soft">Откликнуться</button></div></div>
    </section>
    <section class="box"><div class="box-h"><h2>Условия</h2></div><div class="box-b prose"><p>Команды до 4 человек или соло. Любой движок. Готовые ассеты можно, если указаны лицензии. Игру нужно загрузить на itch.io до конца джема.</p></div></section>
  </main>
  <aside class="side-stack">
    <section class="cta-box"><h2>Нет команды?</h2><p>Соберите свою под этот джем — участники увидят её в списке.</p><button class="btn hl">Создать команду</button></section>
    <section class="box"><div class="box-h"><h2>Детали</h2></div><div class="box-b"><dl class="facts"><dt>Тип</dt><dd>game jam</dd><dt>Формат</dt><dd>онлайн</dd><dt>Даты</dt><dd>16–19 окт</dd><dt>Часовой пояс</dt><dd>МСК</dd><dt>Команда</dt><dd>до 4 человек</dd></dl></div></section>
    <div class="source"><span>Источник: <b>itch.io</b> · организатор Pixel Club. Krug не проводит этот джем.</span></div>
  </aside>
</div>''')

# ---------- TEAM ----------
page("team.html","Тихая станция","Команды",f'''
<section class="page-head" style="--c:var(--c-team)"><div class="wrap">
  <div class="crumbs"><a href="#">Команды</a><span>/</span><span>Тихая станция</span></div>
  <div class="head-grid">
    <div class="emblem">Т</div>
    <div><h1 class="page-title">Тихая станция</h1><p class="page-sub">Нарративный хоррор на Godot для Осеннего пиксель-джема.</p>
      <div class="head-meta"><span class="kind-l">Команда</span><span>на <b>Осенний пиксель-джем</b></span><span><b>2 из 4</b> мест</span><span>UTC+3 · вечера</span></div></div>
    <div class="head-actions">{SAVE}{SHARE}<a class="btn hl" href="#">Откликнуться</a></div>
  </div>
</div></section>
<div class="subnav"><div class="wrap"><nav><a aria-current="page" href="#">Обзор</a><a href="#">Роли<span class="num">2</span></a><a href="#">Участники<span class="num">2</span></a></nav></div></div>
<div class="wrap detail">
  <main>
    <section class="box"><div class="box-h"><h2>Состав</h2><span class="status reg">набор открыт</span></div><div class="box-b"><div class="slots" style="gap:.6rem">
      <span class="slot"><i>АК</i>Алексей · Godot</span><span class="slot"><i>ЛМ</i>Лиза · сценарий</span><span class="slot open"><i></i>2D-художник</span><span class="slot open"><i></i>звук</span></div></div></section>
    <section class="box"><div class="box-h"><h2>Кого ищем</h2></div>
      <div class="role"><h3>2D-художник</h3><p>Пиксель-арт персонажей и окружения, 32×32. Палитра и референсы уже есть.</p><div class="meta"><span>на 72 часа джема</span><span>UTC+2…+5</span></div><div class="act"><button class="btn soft">Откликнуться</button></div></div>
      <div class="role"><h3>Звук</h3><p>Эмбиент и звуки станции, немного музыки на меню.</p><div class="meta"><span>на 72 часа джема</span><span>любой пояс</span></div><div class="act"><button class="btn soft">Откликнуться</button></div></div>
    </section>
    <section class="box"><div class="box-h"><h2>Идея</h2></div><div class="box-b prose"><p>Ночной смотритель заброшенной станции метро слышит поезда, которых нет в расписании. Хотим сделать короткую игру на 15 минут с упором на звук и свет.</p></div></section>
  </main>
  <aside class="side-stack">
    <section class="cta-box"><h2>Событие команды</h2><p>Осенний пиксель-джем · старт через 3 дня 14 часов.</p><a class="btn hl" href="#">Страница джема</a></section>
    <section class="box"><div class="box-h"><h2>Детали</h2></div><div class="box-b"><dl class="facts"><dt>Движок</dt><dd>Godot 4</dd><dt>Язык</dt><dd>русский</dd><dt>Созвоны</dt><dd>Discord, вечером</dd><dt>Создана</dt><dd>8 окт 2026</dd></dl></div></section>
  </aside>
</div>''')

# ---------- PROFILE ----------
page("profile.html","Вера Соколова","Поиск",f'''
<section class="page-head" style="--c:var(--c-person)"><div class="wrap">
  <div class="crumbs"><a href="#">Люди</a><span>/</span><span>Вера Соколова</span></div>
  <div class="head-grid">
    <div class="emblem round">ВС</div>
    <div><h1 class="page-title">Вера Соколова</h1><p class="page-sub">Саунд-дизайнер. Делаю звук и музыку для небольших игр, люблю нарратив и хоррор.</p>
      <div class="head-meta"><span class="kind-l">Открыта к сотрудничеству</span><span>UTC+3</span><span>русский, english</span><span>вечера и выходные</span></div></div>
    <div class="head-actions">{SHARE}<a class="btn hl" href="#">Пригласить в проект</a></div>
  </div>
</div></section>
<div class="wrap detail">
  <main>
    <section class="box"><div class="box-h"><h2>Чем хочет заниматься</h2></div><div class="box-b prose"><p>Ищу джем-команду или небольшой проект на пару месяцев. Интересны нарративные игры, хоррор, всё, где звук — часть геймплея.</p></div></section>
    <div class="two">
      <section class="box"><div class="box-h"><h2>Навыки</h2></div><div class="box-b"><div class="tags"><span class="tag">звук</span><span class="tag">музыка</span><span class="tag">FMOD</span><span class="tag">Reaper</span><span class="tag">Wwise</span></div></div></section>
      <section class="box"><div class="box-h"><h2>Хочет освоить</h2></div><div class="box-b"><div class="tags"><span class="tag">Godot</span><span class="tag">процедурный звук</span></div></div></section>
    </div>
    <section class="box"><div class="box-h"><h2>Проекты и команды</h2></div>
      <div class="role"><h3>Карта шумов</h3><p>Участник · frontend и звук</p><div class="meta"><span>проект · на хакатон</span></div><div class="act"><a class="btn line" href="#" style="color:var(--ink);border-color:var(--line)">Открыть</a></div></div>
      <div class="role"><h3>Инди-звук по-русски</h3><p>Участник сообщества</p><div class="meta"><span>сообщество · 214 участников</span></div><div class="act"><a class="btn line" href="#" style="color:var(--ink);border-color:var(--line)">Открыть</a></div></div>
    </section>
  </main>
  <aside class="side-stack">
    <section class="box"><div class="box-h"><h2>Видимость</h2></div>
      <div class="toggle"><div><b>Показывать в поиске людей</b><div style="color:var(--muted);font-size:.88rem">Профиль виден всем; email не показывается</div></div><span class="switch" role="img" aria-label="включено"></span></div>
    </section>
    <section class="box"><div class="box-h"><h2>Ссылки</h2></div><div class="links"><a href="#">Портфолио <span>itch.io</span></a><a href="#">Музыка <span>SoundCloud</span></a><a href="#">GitHub <span>vsokolova</span></a></div></section>
  </aside>
</div>''')
print("ok")
