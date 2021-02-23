import json, requests

from django.http      import JsonResponse
from django.views     import View
from django.db.models import (
    Sum,
    Count
)

from .models          import Library, LibraryBook
from user.models      import User, UserBook
from book.models      import Book
from share.decorators import check_auth_decorator


class MyLibraryView(View):
    @check_auth_decorator
    def post(self, request):
        data = json.loads(request.body)
        try:
            user      = request.user
            book_id   = data['book_id']
            library   = Library.objects.filter(user_id=user)
            nickname  = User.objects.get(id=user).nickname

            if not library:
                library = Library.objects.create(
                    user_id = user,
                    name    = nickname
                )
                return JsonResponse({'message':'CREATED_LIBRARY'}, status=200)
            if LibraryBook.objects.filter(book_id=book_id, library_id=library.first().id).exists():
                return JsonResponse({'message':'ALREADY_BOOK'}, status=400)
            book_save  = LibraryBook.objects.create(
                book_id    = book_id,
                library_id = library.first().id
            )
            return JsonResponse({'book_save':'SUCCESS'}, status=200)
        except KeyError:
            return JsonResponse({'message':'INVAILD_KEYS'}, status=400)


class LibraryBookListView(View):
    """
    내 서재 책 리스트 정렬 및 조회

    Author: 고수희

    History: 2020-12-10(고수희) : 초기 생성
             2020-12-11(고수희) : 1차 수정 - 정렬 변경
             2021-01-20(고수희) : 2차 수정 - 변수 명 수정, 주석 추가

    Returns: 내 서재 책 리스트

    """

    @check_auth_decorator
    def get(self, request):
        user_id  = request.user
        ordering = request.GET.get('ordering', '1')  # 책 정렬 순서

        conditions = {
            1: '-created_at',  # 생성일자 내림차순
            2: 'book__title',  # 책 제목순
            3: 'book__author',  # 책 저자 순
            4: '-book__publication_date'  # 책 출간일 내림차순
        }

        books = LibraryBook.objects.select_related(
            'book', 'library').filter(
                library__user_id=user_id).order_by(conditions[int(ordering)])

        book_list = {
            "libraryBook" : [{
                "id"     : library.book.id,  # 책 id
                "title"  : library.book.title,  # 책 제목
                "image"  : library.book.image_url,  # 책 표지 이미지
                "author" : library.book.author  # 책 저자
            } for library in books]}
        return JsonResponse(book_list, status=200)


class StatisticsView(View):
    @check_auth_decorator
    def get(self, request):
        result = {}

        # 사용자의 총 독서권수, 총 독서시간        
        userbook = UserBook.objects.select_related('user', 'book').filter(user_id = request.user)
        
        result['total_book_count'] = userbook.count()
        result['total_read_time']  = userbook.aggregate(total_read_time=Sum('time'))['total_read_time']
        if not result['total_read_time']:
            result['total_read_time'] = 0            
        
        # 추천 책 선정
        if not result['total_book_count']:
            result['recommand_book'] = list(Book.objects.all().order_by('-publication_date').values('id', 'title', 'image_url', 'author')[:1])[0]
        else:
            count_of_category = list(userbook.values('book__category_id').annotate(count = Count('book__category_id')))
            target            = max(count_of_category, key=lambda x:x['count'])
            category_id       = target['book__category_id']
                    
            books = Book.objects.filter(category_id=category_id).order_by('-publication_date')
            if books:
                result['recommand_book'] = list(books.values('id', 'title', 'image_url', 'author'))[0]
        
        return JsonResponse({"message":"SUCCESS", "data":result}, status=200)


class LibraryInfoView(View):
    """
    내 서재 정보 조회

    Author: 고수희

    History: 2020-12-10(고수희) : 초기 생성
             2020-12-11(고수희) : 1차 수정 - url 수정 및 토큰 user id 삭제
             2021-01-20(고수희) : 2차 수정 - 변수 명 수정, 주석 추가

    Returns: 내 서재 정보

    """

    @check_auth_decorator
    def get(self, request):
        user_id = request.user

        library_info = {
            "libraryInfo" : [{
                "libraryName"  : library.name,  # 서재 이름
                "libraryImage" : library.image_url,  # 서재 백그라운드 이미지
                "userName"     : library.user.nickname,  # 사용자 닉네임
                "userImage"    : library.user.image_url  # 사용자 프로필 이미지
                    if library.user.image_url is not None
                    else '',
            } for library in Library.objects.filter(
                user_id=user_id)]}

        return JsonResponse (library_info, status=200)
