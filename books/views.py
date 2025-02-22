from django.shortcuts import render,redirect
from django.http import HttpResponse
from . import models
from django.views.generic import DetailView
from . import forms
from . import models
from transactions.models import Transaction
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from transactions.constants import BOOKED,RETURN
from transactions.views import send_transaction_email
# Create your views here.

from django.shortcuts import redirect
from django.http import HttpResponseForbidden, HttpResponse
from django.views.generic.detail import DetailView
from . import models, forms

class DetailBookView(DetailView):
    model = models.Book
    pk_url_kwarg = 'id'
    template_name = 'book_details.html'

    def post(self, request, *args, **kwargs):
        book = self.get_object()

        # Prevent guests from submitting reviews
        if not request.user.is_authenticated:
            return HttpResponseForbidden("You need to log in to submit a review.")

        review_form = forms.ReviewForm(data=request.POST)

        # Check if user has borrowed the book
        borrows = models.Borrow.objects.filter(user=request.user, book=book)
        if not borrows.exists():
            return HttpResponseForbidden("You can only review books you have borrowed.")

        # Check if user has already reviewed the book
        if models.Review.objects.filter(user=request.user, book=book).exists():
            return HttpResponseForbidden("You have already reviewed this book.")

        # Save the review if form is valid
        if review_form.is_valid():
            new_review = review_form.save(commit=False)
            new_review.user = request.user
            new_review.book = book
            new_review.save()
            return self.get(request, *args, **kwargs)  # Refresh the page after submission

        return HttpResponse("Invalid form submission. Please try again.")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        book = self.object
        context['reviews'] = book.reviews.all()
        context['reviews_form'] = forms.ReviewForm()
        context['user_authenticated'] = self.request.user.is_authenticated  # Pass authentication status
        return context


@login_required
def borrow_book(request, id):
    book = models.Book.objects.get(pk=id)
    user_account = request.user.account

    if user_account.balance >= book.borrowing_price:
        user_account.balance -= book.borrowing_price
        user_account.save()
        borrow = models.Borrow(user=request.user, book=book)
        Transaction.objects.create(
          account=user_account,
          amount=book.borrowing_price,
          transaction_type=BOOKED,
          balance_after_transaction=user_account.balance
          )
        # borrow_book_email.html
        send_transaction_email(request.user, book.borrowing_price, "Borrow Book", "borrow_book_email.html")
        borrow.save()
        return redirect('profile')
    
@login_required
def all_borrow_book(request):
    borrow_book = models.Borrow.objects.all()
    return render(request,'borrow_book.html',{'borrow_book':borrow_book})



@login_required
def return_book(request, id):
    borrow_book = models.Borrow.objects.get(pk=id)
    user_account = request.user.account

    user_account.balance+=borrow_book.book.borrowing_price
    user_account.save(
            update_fields=[
                'balance'
            ]
        )
    
    borrow_book.returned=True
    borrow_book.save(
            update_fields=[
                'returned'
            ]
        )
    
    Transaction.objects.create(
      account=user_account,
      amount=borrow_book.book.borrowing_price,
      transaction_type=RETURN,
      balance_after_transaction=user_account.balance
      )
    send_transaction_email(request.user, borrow_book.book.borrowing_price, "Return  Book", "return_book_email.html")
    return redirect('all_borrow_book')