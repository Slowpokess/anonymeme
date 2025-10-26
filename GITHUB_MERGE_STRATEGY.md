# 🔀 GitHub Merge Strategy Guide

## Проблема

В репозитории Anonymeme PR мержатся с опцией "Create a merge commit", что приводит к:
- Множеству коммитов в main ветке
- "Грязной" истории Git
- Сложности в поиске изменений

**Пример:**
- PR #1: 17 коммитов попало в main
- PR #7: 4 коммита попало в main
- PR #8: merge коммит

## Рекомендуемое решение

### 🎯 Использовать "Squash and merge" по умолчанию

**Преимущества:**
- ✅ Один коммит на PR в main ветке
- ✅ Чистая история Git
- ✅ Легко откатить изменения (revert одного коммита)
- ✅ Проще делать code review истории
- ✅ Линейная история без merge commits

**Пример:**
```
До (merge commit):
main: A---B---C---D---E---F---G---H---I---J---K (17 коммитов)

После (squash):
main: A---B---C (1 коммит на PR)
```

## 🔧 Как настроить

### На GitHub (в Settings)

1. Зайдите в **Settings** → **General**
2. Прокрутите до секции **"Pull Requests"**
3. **Отключите:**
   - ❌ Allow merge commits
   - ❌ Allow rebase merging
4. **Включите:**
   - ✅ Allow squash merging
5. **Установите:**
   - Default to squash merging

### Или через .github/settings.yml (если используете probot/settings)

```yaml
repository:
  # Merge strategy
  allow_squash_merge: true
  allow_merge_commit: false
  allow_rebase_merge: false

  # Default merge method
  default_merge_method: squash

  # Squash PR title as commit message
  squash_merge_commit_title: PR_TITLE
  squash_merge_commit_message: PR_BODY
```

## 📝 Как правильно мержить PR

### При создании PR

1. **Делайте коммиты как обычно** в feature ветке
2. Не беспокойтесь о количестве коммитов
3. Пишите понятные commit messages для себя

### При merge PR

1. **На GitHub выберите "Squash and merge"**
2. **Отредактируйте commit message:**
   ```
   feat: добавить feature X

   - Детали изменения 1
   - Детали изменения 2
   - Детали изменения 3

   Closes #123
   ```
3. **Нажмите "Confirm squash and merge"**

### Результат

В main попадет **один чистый коммит** с описательным сообщением.

## 🚫 Что делать с уже смердженными PR

К сожалению, для **уже смердженных PR ничего нельзя сделать** без переписывания истории main, что опасно для публичного репозитория.

**Почему нельзя:**
- История main уже опубликована
- Другие разработчики могут базироваться на этих коммитах
- Force push в main - это плохая практика
- Можно сломать существующие PR

**Что можно:**
- ✅ Принять как есть
- ✅ Настроить правильную стратегию для будущих PR
- ✅ Двигаться дальше с чистой историей

## 📊 Сравнение стратегий

| Стратегия | Преимущества | Недостатки | Когда использовать |
|-----------|--------------|------------|-------------------|
| **Squash and merge** | Чистая история, один коммит на PR | Теряется детальная история коммитов | Для большинства PR |
| Merge commit | Сохраняется вся история | Грязная история с merge commits | Редко |
| Rebase and merge | Линейная история без merge commits | Сложнее, нужен force push | Для продвинутых команд |

## 🎓 Best Practices

### ✅ Хорошо

```bash
# В feature ветке делайте коммиты как удобно
git commit -m "wip: working on feature"
git commit -m "fix typo"
git commit -m "add tests"
git commit -m "fix linting"

# При merge на GitHub используйте Squash and merge
# Результат в main:
# feat: implement user authentication system
```

### ❌ Плохо

```bash
# Мержить через "Create a merge commit"
# Результат в main:
# Merge pull request #123
#   wip: working on feature
#   fix typo
#   add tests
#   fix linting
```

## 🔍 Как проверить текущую настройку

```bash
# Посмотреть историю main
git log --oneline --graph main -20

# Если видите много merge commits и коммитов типа "fix typo",
# значит используется merge commit стратегия
```

## 📚 Дополнительные ресурсы

- [GitHub Docs: About merge methods](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/about-merge-methods-on-github)
- [Git Best Practices: Commit Often, Perfect Later, Publish Once](https://sethrobertson.github.io/GitBestPractices/)

---

## ✅ Action Items

### Немедленно (для владельца репозитория)

1. Зайти в Settings → General → Pull Requests
2. Выключить "Allow merge commits"
3. Выключить "Allow rebase merging"
4. Включить "Allow squash merging"
5. Установить "Default to squash merging"

### Для всех разработчиков

1. При создании PR на GitHub всегда выбирать "Squash and merge"
2. Редактировать commit message перед merge
3. Включать номер issue/PR в commit message (например, "Closes #123")

---

**Статус:** Готово к применению
**Требуется:** Права администратора репозитория для изменения Settings
