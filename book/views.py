import json
import datetime
from datetime         import timedelta, date

from django.views     import View
from django.db        import transaction
from django.db.models import Q, Count
from django.http      import JsonResponse

from .models          import (
    Book,
    Category,
    Keyword,
    Today,
    Review,
    Like,
)
from library.models   import (
        Library,
        LibraryBook,
)
from user.models      import UserBook

from .modules.numeric import get_reading_numeric
from share.decorators import check_auth_decorator

class TodayBookView(View):
    """
    오늘의 추천 책 조회

    Author: 고수희

    History: 2020-11-24(고수희) : 초기 생성
             2020-11-27(고수희) : 1차 수정 - 리스트 조회 시 대댓글 리스트도 함께 나오도록 수정
             2021-01-20(고수희) : 2차 수정 - 변수 명 수정, 주석 추가

    Returns: 댓글 정보 리스트

    """

    def get(self, request):

        today      = date.today().strftime('%Y-%m-%d')
        today_book = Book.objects.prefetch_related(
            'review_set','review_set__like_set').filter(today__pick_date=today)

        if not today_book.exists():
            return JsonResponse({"message":"NO_BOOK"}, status = 400)

        today_review = today_book.first().review_set.prefetch_related(
            'like_set').values('user__nickname', 'user__image_url',
                               'contents').annotate(count=Count(
                                   'likes')).order_by('-count')[:1].first()

        book = [{
            "id"             : book.id,
            "title"          : book.title,
            "image"          : book.image_url,
            "author"         : book.author,
            "description"    : book.today_set.get(book_id=book).description,
            "reviewerName"   : today_review.get('user__nickname'),
            "reviewerImage"  : today_review.get('user__image_url')
                if today_review.get('user__image_url') is not None
                else '',
            "reviewContent"  : today_review.get('contents'),
        } for book in today_book]
        return JsonResponse({"todayBook":book}, status = 200)


class RecentlyBookView(View):
    """
    최근 출간 (1달 이전 출간) 책 리스트 조회

    Author: 고수희

    History: 2020-12-03(고수희) : 초기 생성
             2020-12-03(고수희) : 1차 수정 - querystring 처리
             2020-12-03(고수희) : 2차 수정 - 변수 삭제 및 구조 수정
             2021-02-08(고수희) : 3차 수정 - 주석 추가

    Returns: 최근 1달 이전에 출간된 책 리스트

    """

    def get(self, request):
        day    = request.GET.get('day', '30')  # 조회할 출간 일자 : 기본값 30일
        limit  = request.GET.get('limit', '10')  # 출력할 책 리스트의 갯수 : 기본값 10일

        today          = date.today()  # 오늘 날짜 조회
        previous_days  = today - timedelta(days=int(day))  # 오늘 날짜 기준 조회할 출간일자

        books = [{
            "id"     : book.id,  # 책 id
            "title"  : book.title,  # 책 타이틀
            "image"  : book.image_url,  # 책 표지 이미지
            "author" : book.author  # 책 저자
            } for book in (Book.objects.filter(
                publication_date__range=[previous_days, today])
                .order_by('-publication_date')[:int(limit)])]

        if not books:
            return JsonResponse({"message": "NO_BOOKS"}, status=400)
        return JsonResponse({"oneMonthBook": books}, status=200)

class BookDetailView(View):
    def get(self, request, book_id):
        try :
            data = get_reading_numeric(book_id)
            book = Book.objects.select_related('category').prefetch_related('review_set').get(id=book_id)
            book_detail = {
                'title'            : book.title,
                'subtitle'         : book.subtitle,
                'image_url'        : book.image_url,
                'company'          : book.company,
                'author'           : book.author,
                'contents'         : book.contents,
                'company_review'   : book.company_review,
                'page'             : book.page,
                'publication_date' : book.publication_date,
                'description'      : book.description,
                'category'         : book.category.name,
                'review_count'     : book.review_set.count(),
                'reder'            : book.userbook_set.count(),
                'numeric'          : data
                }
            return JsonResponse({'book_detail':book_detail, 'like':False}, status=200)
        except Book.DoesNotExist:
            return JsonResponse({'message':'NOT_EXIST_BOOK'}, status=400)

class CommingSoonBookView(View):
    """
    출간 예정 책(당일 기준 1달 이내) 리스트 조회

    Author: 고수희

    History: 2020-12-04(고수희) : 초기 생성
             2020-12-04(고수희) : 1차 수정 - 변수 명 수정
             2021-02-08(고수희) : 2차 수정 - 주석 추가

    Returns: 1달 이내 출간 책 리스트

    """

    def get(self, request):
        day    = request.GET.get('day', '30')  # 조회할 출간 일자 : 기본값 30일
        limit  = request.GET.get('limit', '10')  # 츨력할 책 리스트 갯수: 기본값 10일

        today            = date.today()  # 오늘 날짜 조회
        next_publication = today + timedelta(days=int(day))  # 조회할 다음 출간일
        min_day          = today + timedelta(days=1)  # 당일 기준 1일 이내 출간일
        max_day          = today + timedelta(days=5)  # 당일 기준 5일 이내 출간일

        book_list = [{
            "id"     : book.id,  # 책 id
            "title"  : book.title,  # 책 제목
            "image"  : book.image_url,  # 책 표지 이미지
            "author" : book.author,  # 책 저자
            "date"   : (book.publication_date - today).days  # 5일 이내에 출간 예정이면 일자 표현, 이후 출간이면 "n월 n일" 형태로 출력
                if min_day <= book.publication_date <= max_day
                else book.publication_date.strftime('%m월%d')
        } for book in (Book.objects.filter(
            publication_date__range=[min_day, next_publication]).order_by
            ('publication_date')[:int(limit)])]  # 출간일 순으로 오름차순으로 출력

        if not book_list:
            return JsonResponse({"message": "NO_BOOKS"}, status=400)
        return JsonResponse({"commingSoonBook": book_list}, status=200)


class SearchBookView(View):
    def get(self, request):
        conditions = {
                'author__icontains'  : request.GET.get('author', ''),
                'title__icontains'   : request.GET.get('title', ''),
                'company__icontains' : request.GET.get('company', ''),
        }

        for key, value in conditions.items():
            if value:
                or_conditions.add(Q(**{key: value}), Q.OR)

        if or_conditions:
            json_data = list(
                            Book.objects.filter(or_conditions).values(
                                'id',
                                'author',
                                'title',
                                'image_url',
                                'company'
                                )
                        )
            return JsonResponse({"message":"SUCCESS", "books":json_data}, status=200)

        return JsonResponse({"message":"INVALID_REQUEST"}, status=400)

class ReviewView(View):
    @check_auth_decorator
    def post(self, request, book_id):
        data = json.loads(request.body)
        try :
            user_id  = request.user
            contents = data['contents']

            if len(contents) < 200:
                review = Review.objects.create(
                    user_id  = user_id,
                    book_id  = book_id,
                    contents = contents
                )
                return JsonResponse({'message':'SUCCESS'}, status=200)
            return JsonResponse({'message':'LONG_CONTENTS'}, status=400)
        except KeyError:
            return JsonResponse({'message':'KEY_ERROR'}, status=400)

    def get(self, request, book_id):
        try:
            reviews = Book.objects.get(id=book_id).review_set.all()
            review_list = [{
                'review_id'  : review.id,
                'nick_name'  : review.user.nickname,
                'user_img'   : review.user.image_url,
                'content'    : review.contents,
                'created_at' : review.created_at.strftime('%Y.%m.%d'),
            } for review in reviews ]
            return JsonResponse({'review_list':review_list}, status=200)
        except Review.DoesNotExist:
            return JsonResponse({'message':'NOT_EXIST_REVIEW'}, status=400)

    @check_auth_decorator
    def delete(self, request, book_id):
        try :
            user_id   = request.user
            review_id = request.GET['review_id']
            review    = Review.objects.get(id=review_id)
            if review.user_id == user_id:
                review.delete()
                return JsonResponse({'message':'SUCCESS'}, status=200)
            return JsonResponse({'message':'UNAUTHORIZED'}, status=400)
        except Review.DoesNotExist:
            return JsonResponse({'message':'NOT_EXIST_REVIEW'}, status=400)

class ReviewLikeView(View):
    @check_auth_decorator
    def patch(self, request):
        data = json.loads(request.body)
        try:
            user_id    = request.user
            review_id  = data['review_id']

            if Review.objects.filter(id=review_id).exists():
                like = Like.objects.get(user_id=user_id, review_id=review_id)
                like.delete()
                return JsonResponse({'message':'CANCEL', 'like':False}, status=200)
            return JsonResponse({'message':'NOT_EXIST_REVIEW'}, status=400)
        except Like.DoesNotExist:
            Like.objects.create(user_id=user_id, review_id=review_id)
            return JsonResponse({'message':'SUCCESS'}, status=200)

class BestSellerBookView(View):
    """
    사용자 서재에 가장 많이 담긴 베스트 셀러 책 리스트 조회

    Author: 고수희

    History: 2020-11-24(고수희) : 초기 생성
             2020-11-27(고수희) : 1차 수정 - 리스트 조회 시 대댓글 리스트도 함께 나오도록 수정
             2021-01-20(고수희) : 2차 수정 - 변수 명 수정, 주석 추가

    Returns: 베스트셀러 책 리스트

    """

    def get(self, request):
        keyword = request.GET.get('keyword', '1')  # 태그의 번호
        limit   = request.GET.get('limit', '10')  # 출력할 책의 갯수

        if int(keyword) in range(2,7):
           books = UserBook.objects.select_related('book').filter(
               book__keyword_id=int(keyword)).annotate(count=Count(
                   'book_id')).order_by('-count')[:int(limit)]
           if not books:
               return JsonResponse({"message": "NO_BOOKS"}, status=400)

        else:
           books = UserBook.objects.select_related('book').filter(
               book__keyword_id__gte=2).annotate(count=Count(
                   'book_id')).order_by('-count')[:int(limit)]
           if not books:
               return JsonResponse({"message": "NO_BOOKS"}, status=400)

        book_list = [{
            "id"     : book.book.id,  # 책 id
            "title"  : book.book.title,  # 책 제목
            "image"  : book.book.image_url,  # 책 표지 이미지
            "author" : book.book.author  # 책 저자
        } for book in books]
        return JsonResponse ({"bestSellerBook":book_list}, status=200)

class RecommendBookView(View):
    """
    해당 주간에 사용자 서재에 가장 많이 담긴 추천 책 조회

    Author: 고수희

    History: 2020-11-24(고수희) : 초기 생성
             2020-11-27(고수희) : 1차 수정 - 리스트 조회 시 대댓글 리스트도 함께 나오도록 수정
             2021-01-10(고수희) : 2차 수정 - 변수 명 수정, 주석 추가

    Returns: 추천 책 리스트

    """


    def get(self, request):
        keyword    = request.GET.get('keyword', '2')  # 태그 번호
        limit      = request.GET.get('limit', '6')  # 출력할 책의 갯수

        today_iso  = datetime.datetime.now().isocalendar()
        year       = today_iso[0]  # 현재년도
        week       = today_iso[1]  # 현재 날짜 (월)

        week_start = date.fromisocalendar(year, week, 1)  # 한 주의 가장 첫 시작 일요일 추출
        now        = datetime.datetime.now()  # 오늘 날짜

        books = LibraryBook.objects.prefetch_related('book_set').filter(
            created_at__range=[week_start, now], book__keyword_id=int(
                keyword)).values('book_id', 'book__title', 'book__image_url',
                                'book__author').annotate(count=Count(
                    'book_id')).order_by('-count')[:int(limit)]

        book_list = [
            {
                "id"     : book.get('book_id'),  # 책 id
                "title"  : book.get('book__title'),  # 책 제목
                "image"  : book.get('book__image_url'),  # 책 표지 이미지
                "author" : book.get('book__author')  # 책 저자
            } for book in books]

        if not book_list:
            return JsonResponse({"message": "NO_BOOKS"}, status=400)
        return JsonResponse({"recommendBook": book_list}, status=200)

class LandingPageView(View):
    def get(self, request):
        maximum_count = int(request.GET.get('maximum', 60))

        result = [
            {
                'id'        : book.id,
                'image_url' : book.image_url
            } for book in Book.objects.exclude(image_url='')[0:maximum_count]
        ]

        return JsonResponse({"message":"SUCCESS", "books":result}, status=200)
