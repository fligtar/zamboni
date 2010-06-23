import logging

from django.db.models import Count, Avg, Sum

from celery.decorators import task
import caching.base as caching

from addons.models import Addon
from .models import Review

log = logging.getLogger('z.task')


@task(rate_limit='50/m')
def update_denorm(*pairs, **kw):
    """
    Takes a bunch of (addon, user) pairs and sets the denormalized fields for
    all reviews matching that pair.
    """
    log.info('[%s@%s] Updating review denorms.' %
             (len(pairs), update_denorm.rate_limit))
    for addon, user in pairs:
        reviews = list(Review.uncached.filter(addon=addon, user=user)
                       .filter(reply_to=None).order_by('created'))
        if not reviews:
            continue

        for idx, review in enumerate(reviews):
            review.previous_count = idx
            review.is_latest = False
        reviews[-1].is_latest = True

        for review in reviews:
            review.save()


@task
def addon_review_aggregates(*addons, **kw):
    log.info('[%s@%s] Updating total reviews.' %
             (len(addons), addon_review_aggregates.rate_limit))
    stats = (Review.objects.valid().filter(addon__in=addons)
             .values_list('addon').annotate(Count('addon')))
    for addon, count in stats:
        Addon.objects.filter(id=addon).update(total_reviews=count)

    log.info('[%s@%s] Updating average ratings.' %
             (len(addons), addon_review_aggregates.rate_limit))
    stats = (Review.objects.valid().filter(addon__in=addons)
             .values_list('addon').annotate(Avg('rating')))
    for addon, avg in stats:
        Addon.objects.filter(id=addon).update(average_rating=avg)

    # Delay bayesian calculations to avoid slave lag.
    addon_bayesian_rating.apply_async(args=addons, countdown=5)


@task
def addon_bayesian_rating(*addons, **kw):
    log.info('[%s@%s] Updating bayesian ratings.' %
             (len(addons), addon_bayesian_rating.rate_limit))
    f = lambda: Addon.objects.aggregate(rating=Avg('average_rating'),
                                        reviews=Avg('total_reviews'))
    avg = caching.cached(f, 'task.bayes.avg', 60 * 60 * 60)
    qs = (Addon.uncached.filter(id__in=addons, total_reviews__gt=0)
          .annotate(sum_ratings=Sum('_reviews__rating')))
    for addon in qs:
        if addon.total_reviews and addon.sum_ratings:
            num = (avg['reviews'] * avg['rating']) + addon.sum_ratings
            denom = avg['reviews'] + addon.total_reviews
            addon.bayesian_rating = float(num) / denom
        else:
            addon.bayesian_rating = 0
        addon.save()


@task(rate_limit='10/m')
def cron_review_aggregate(*addons, **kw):
    log.info('[%s@%s] Updating addon review aggregates.' %
             (len(addons), cron_review_aggregate.rate_limit))
    # We have this redundant task to get rate limiting for big chunks.
    addon_review_aggregates(*addons)