import vk_api
import logging
from PySide6.QtCore import QObject, Signal
from urllib.parse import urlparse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VKClient(QObject):
    progress_updated = Signal(int)

    def __init__(self, access_token):
        super().__init__()
        self.vk_session = vk_api.VkApi(token=access_token)
        self.vk = self.vk_session.get_api()

    def get_posts(self, group_url, max_count=100):
        logger.info(f"Загрузка постов для группы: {group_url}")
        try:
            # Извлечение screen_name из URL
            parsed_url = urlparse(group_url)
            path = parsed_url.path.strip('/')
            if not path:
                logger.error("Неверный формат URL группы")
                raise ValueError("Неверный формат URL группы")

            # Получение group_id
            group_info = self.vk.groups.getById(group_id=path)
            if not group_info:
                logger.error("Группа не найдена")
                raise ValueError("Группа не найдена")
            group_id = group_info[0]['id']

            posts = []
            offset = 0
            count_per_request = min(max_count, 100)  # VK API ограничение: до 100 постов за запрос

            while offset < max_count:
                self.progress_updated.emit(int((offset / max_count) * 100))
                response = self.vk.wall.get(owner_id=-group_id, count=count_per_request, offset=offset)
                items = response.get('items', [])
                if not items:
                    break

                for item in items:
                    post = {
                        'owner_id': item['owner_id'],
                        'post_id': item['id'],
                        'date': item['date'],
                        'text': item.get('text', ''),
                        'comments_count': item.get('comments', {}).get('count', 0)
                    }
                    posts.append(post)
                    if len(posts) >= max_count:
                        break

                offset += count_per_request
                if len(posts) >= max_count or len(items) < count_per_request:
                    break

            self.progress_updated.emit(100)
            logger.info(f"Успешно загружено {len(posts)} постов")
            return posts

        except vk_api.exceptions.ApiError as e:
            logger.error(f"Ошибка VK API при загрузке постов: {e}")
            self.progress_updated.emit(100)
            raise
        except Exception as e:
            logger.error(f"Не удалось загрузить посты: {e}")
            self.progress_updated.emit(100)
            raise

    def get_comments(self, post_url, max_count=100):
        logger.info(f"Загрузка комментариев для поста: {post_url}")
        try:
            # Извлечение owner_id и post_id из URL
            parsed_url = urlparse(post_url)
            path = parsed_url.path.strip('/')
            if not path.startswith('wall'):
                logger.error("Неверный формат URL поста")
                raise ValueError("Неверный формат URL поста")

            owner_id, post_id = path.replace('wall', '').split('_')
            owner_id = int(owner_id)
            post_id = int(post_id)

            comments = []
            offset = 0
            count_per_request = min(max_count, 100)  # VK API ограничение: до 100 комментариев за запрос

            while offset < max_count:
                self.progress_updated.emit(int((offset / max_count) * 100))
                response = self.vk.wall.getComments(
                    owner_id=owner_id,
                    post_id=post_id,
                    count=count_per_request,
                    offset=offset,
                    need_likes=0,
                    preview_length=0
                )
                items = response.get('items', [])
                if not items:
                    break

                for item in items:
                    # Получение автора комментария
                    author_id = item.get('from_id', 0)
                    author_name = "Unknown"
                    try:
                        if author_id > 0:
                            user = self.vk.users.get(user_ids=author_id)[0]
                            author_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
                        elif author_id < 0:
                            group = self.vk.groups.getById(group_id=-author_id)[0]
                            author_name = group.get('name', 'Group')
                    except Exception as e:
                        logger.warning(f"Не удалось получить автора комментария {author_id}: {e}")

                    comment = {
                        'author': author_name,
                        'date': item['date'],
                        'text': item.get('text', '')
                    }
                    comments.append(comment)
                    if len(comments) >= max_count:
                        break

                offset += count_per_request
                if len(comments) >= max_count or len(items) < count_per_request:
                    break

            self.progress_updated.emit(100)
            logger.info(f"Успешно загружено {len(comments)} комментариев")
            return comments

        except vk_api.exceptions.ApiError as e:
            logger.error(f"Ошибка VK API при загрузке комментариев: {e}")
            self.progress_updated.emit(100)
            raise
        except Exception as e:
            logger.error(f"Не удалось загрузить комментарии: {e}")
            self.progress_updated.emit(100)
            raise