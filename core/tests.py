from io import BytesIO

from PIL import Image

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models import ProtectedError
from django.test import RequestFactory, TestCase
from django.urls import reverse

from .admin import ProductAdminForm
from .forms import ContactInquiryForm
from .models import (
    CarouselAd,
    Category,
    CompanyInfo,
    ContactInfo,
    DiscountAnnouncement,
    Product,
)
from .views import submit_inquiry


class ProductAdminFormTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Snacks')

    def base_data(self, specifications, sku=''):
        return {
            'category': str(self.category.pk),
            'name': 'Test Product',
            'sku': sku,
            'description': 'Tasty and crisp.',
            'specifications': specifications,
            'image': '',
            'external_image_url': '',
        }

    def test_accepts_json_specifications(self):
        form = ProductAdminForm(data=self.base_data('{"Net Weight": "400g"}'))
        self.assertTrue(form.is_valid(), form.errors)

        product = form.save()
        self.assertEqual(product.specifications, {'Net Weight': '400g'})

    def test_accepts_key_value_lines(self):
        form = ProductAdminForm(
            data=self.base_data('Net Weight: 400g\nPackaging: Foil pouch')
        )
        self.assertTrue(form.is_valid(), form.errors)

        product = form.save()
        self.assertEqual(
            product.specifications,
            {'Net Weight': '400g', 'Packaging': 'Foil pouch'},
        )

    def test_accepts_plain_text(self):
        form = ProductAdminForm(data=self.base_data('plain text only'))
        self.assertTrue(form.is_valid(), form.errors)

        product = form.save()
        self.assertEqual(product.specifications, {'value': 'plain text only'})

    def test_accepts_malformed_braced_text(self):
        form = ProductAdminForm(data=self.base_data('{12gng}'))
        self.assertTrue(form.is_valid(), form.errors)

        product = form.save()
        self.assertEqual(product.specifications, {'value': '{12gng}'})

    def test_blank_sku_is_normalized_to_none(self):
        form = ProductAdminForm(data=self.base_data('{"Size": "Small"}', sku='   '))
        self.assertTrue(form.is_valid(), form.errors)

        product = form.save()
        self.assertIsNone(product.sku)


class ContactInquiryFormTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_accepts_minimal_payload(self):
        form = ContactInquiryForm(data={
            'name': '',
            'company': '',
            'email': '',
            'phone': '',
            'product_interest': '',
            'message': '',
        })
        self.assertTrue(form.is_valid(), form.errors)

        inquiry = form.save()
        self.assertEqual(inquiry.name, 'Anonymous')
        self.assertTrue(inquiry.email.endswith('@example.com'))

    def test_invalid_email_and_interest_are_safely_normalized(self):
        form = ContactInquiryForm(data={
            'name': '',
            'company': '',
            'email': 'not-an-email',
            'phone': '',
            'product_interest': 'Nope',
            'message': '',
        })
        self.assertTrue(form.is_valid(), form.errors)

        inquiry = form.save()
        self.assertEqual(inquiry.name, 'Anonymous')
        self.assertTrue(inquiry.email.endswith('@example.com'))
        self.assertEqual(inquiry.product_interest, '')

    def test_submit_inquiry_accepts_interest_alias(self):
        request = self.factory.post(
            '/api/inquiry/',
            data='{"name":"A","email":"","interest":"Full Catalog","message":"hi"}',
            content_type='application/json',
        )
        response = submit_inquiry(request)
        self.assertEqual(response.status_code, 200)

    def test_submit_inquiry_rejects_invalid_json(self):
        request = self.factory.post(
            '/api/inquiry/',
            data='not json at all',
            content_type='application/json',
        )
        response = submit_inquiry(request)
        self.assertEqual(response.status_code, 400)


class HomePageBrandingTests(TestCase):
    def test_home_page_renders_aizah_and_not_aiza(self):
        response = self.client.get(reverse('core:home'))
        self.assertEqual(response.status_code, 200)
        body = response.content.decode('utf-8')
        self.assertIn('About Aizah', body)
        self.assertIn('Since 2007, Aizah', body)
        self.assertIn('Aizah FMCG Co. Ltd.', body)
        self.assertNotRegex(body, r'\bAiza\b')


class AdminCrudTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.admin_user = user_model.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='pass12345',
        )
        self.client.force_login(self.admin_user)
        self.primary_category = Category.objects.create(name='Snacks')
        self.secondary_category = Category.objects.create(name='Beverages')

    def make_image(self, name='test.png', size=(48, 48), color=(6, 182, 212)):
        buffer = BytesIO()
        Image.new('RGB', size, color).save(buffer, format='PNG')
        return SimpleUploadedFile(name, buffer.getvalue(), content_type='image/png')

    def test_category_admin_crud_and_unique_slug_generation(self):
        add_url = reverse('admin:core_category_add')

        response = self.client.post(add_url, {
            'name': 'Seasonal Snacks',
            'slug': '',
            '_save': 'Save',
        }, follow=False)
        self.assertEqual(response.status_code, 302)
        category = Category.objects.get(name='Seasonal Snacks')
        self.assertEqual(category.slug, 'seasonal-snacks')

        response = self.client.post(add_url, {
            'name': 'Seasonal Snacks',
            'slug': '',
            '_save': 'Save',
        }, follow=False)
        self.assertEqual(response.status_code, 302)
        slugs = sorted(Category.objects.filter(name='Seasonal Snacks').values_list('slug', flat=True))
        self.assertEqual(slugs, ['seasonal-snacks', 'seasonal-snacks-1'])

        change_url = reverse('admin:core_category_change', args=[category.pk])
        response = self.client.post(change_url, {
            'name': 'Seasonal Snacks Updated',
            'slug': category.slug,
            '_save': 'Save',
        }, follow=False)
        self.assertEqual(response.status_code, 302)
        category.refresh_from_db()
        self.assertEqual(category.name, 'Seasonal Snacks Updated')
        self.assertEqual(category.slug, 'seasonal-snacks')

        delete_url = reverse('admin:core_category_delete', args=[category.pk])
        response = self.client.post(delete_url, {'post': 'yes'}, follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Category.objects.filter(pk=category.pk).exists())

    def test_product_admin_crud_and_blank_sku_regression(self):
        add_url = reverse('admin:core_product_add')

        response = self.client.post(add_url, {
            'category': str(self.primary_category.pk),
            'name': 'Plain Snack',
            'sku': '',
            'description': 'Tasty and crisp.',
            'specifications': 'Net Weight: 400g\nPackaging: Foil pouch',
            'image': self.make_image('plain-snack.png'),
            'external_image_url': '',
        }, follow=False)
        self.assertEqual(response.status_code, 302)
        product = Product.objects.get(name='Plain Snack')
        self.assertIsNone(product.sku)
        self.assertEqual(
            product.specifications,
            {'Net Weight': '400g', 'Packaging': 'Foil pouch'},
        )

        response = self.client.post(add_url, {
            'category': str(self.primary_category.pk),
            'name': 'Plain Snack 2',
            'sku': '   ',
            'description': 'A second product with no SKU should still save.',
            'specifications': '{"Net Weight": "200g"}',
            'image': self.make_image('plain-snack-2.png'),
            'external_image_url': '',
        }, follow=False)
        self.assertEqual(response.status_code, 302)
        second_product = Product.objects.get(name='Plain Snack 2')
        self.assertIsNone(second_product.sku)

        change_url = reverse('admin:core_product_change', args=[product.pk])
        response = self.client.post(change_url, {
            'category': str(self.secondary_category.pk),
            'name': 'Plain Snack XL',
            'sku': 'SNK-100',
            'description': 'Updated description.',
            'specifications': '{"Size": "XL", "Weight": "500g"}',
            'external_image_url': 'https://example.com/product.jpg',
        }, follow=False)
        self.assertEqual(response.status_code, 302)
        product.refresh_from_db()
        self.assertEqual(product.name, 'Plain Snack XL')
        self.assertEqual(product.sku, 'SNK-100')
        self.assertEqual(product.category, self.secondary_category)
        self.assertEqual(
            product.specifications,
            {'Size': 'XL', 'Weight': '500g'},
        )
        self.assertEqual(product.external_image_url, 'https://example.com/product.jpg')

        delete_url = reverse('admin:core_product_delete', args=[second_product.pk])
        response = self.client.post(delete_url, {'post': 'yes'}, follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Product.objects.filter(pk=second_product.pk).exists())

    def test_category_delete_is_protected_when_products_exist(self):
        protected_category = Category.objects.create(name='Protected')
        Product.objects.create(
            category=protected_category,
            name='Protected Product',
            description='This category should not delete.',
        )

        with self.assertRaises(ProtectedError):
            protected_category.delete()

    def test_carousel_ad_admin_crud(self):
        add_url = reverse('admin:core_carouselad_add')
        response = self.client.post(add_url, {
            'title': 'Summer Promo',
            'subtitle': 'Seasonal savings',
            'cta_text': 'Shop now',
            'cta_href': '#products',
            'tag': 'Featured',
            'media_type': 'image',
            'media_file': self.make_image('carousel.png'),
            'external_image_url': '',
            'media_fit': 'contain',
            'order': '3',
            'active': 'on',
            'start_date': '2026-08-01',
            'end_date': '2026-08-31',
            '_save': 'Save',
        }, follow=False)
        self.assertEqual(response.status_code, 302)
        ad = CarouselAd.objects.get(title='Summer Promo')
        self.assertEqual(ad.resolved_media_type(), 'image')
        self.assertEqual(ad.media_fit, 'contain')
        self.assertTrue(ad.active)

        change_url = reverse('admin:core_carouselad_change', args=[ad.pk])
        response = self.client.post(change_url, {
            'title': 'Summer Promo Updated',
            'subtitle': 'Seasonal savings',
            'cta_text': 'Shop now',
            'cta_href': '#products',
            'tag': 'Featured',
            'media_type': 'image',
            'external_image_url': '',
            'media_fit': 'cover',
            'order': '8',
            'start_date': '2026-08-01',
            'end_date': '2026-09-15',
            '_save': 'Save',
        }, follow=False)
        self.assertEqual(response.status_code, 302)
        ad.refresh_from_db()
        self.assertEqual(ad.title, 'Summer Promo Updated')
        self.assertEqual(ad.media_fit, 'cover')
        self.assertEqual(ad.order, 8)
        self.assertFalse(ad.active)

        delete_url = reverse('admin:core_carouselad_delete', args=[ad.pk])
        response = self.client.post(delete_url, {'post': 'yes'}, follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(CarouselAd.objects.filter(pk=ad.pk).exists())

    def test_discount_announcement_admin_crud(self):
        add_url = reverse('admin:core_discountannouncement_add')
        response = self.client.post(add_url, {
            'title': 'Dry Season Deal',
            'description': 'Limited time trade pricing.',
            'badge': 'Active Offer',
            'badge_tone': 'amber',
            'image': self.make_image('offer.png'),
            'external_image_url': '',
            'image_fit': 'contain',
            'meta_text': 'While stock lasts',
            'is_active': 'on',
            'start_date': '2026-08-01',
            'end_date': '2026-08-31',
            '_save': 'Save',
        }, follow=False)
        self.assertEqual(response.status_code, 302)
        offer = DiscountAnnouncement.objects.get(title='Dry Season Deal')
        self.assertEqual(offer.image_fit, 'contain')
        self.assertTrue(offer.is_active)

        change_url = reverse('admin:core_discountannouncement_change', args=[offer.pk])
        response = self.client.post(change_url, {
            'title': 'Dry Season Deal Updated',
            'description': 'Updated trade pricing.',
            'badge': 'Limited',
            'badge_tone': 'brand',
            'external_image_url': '',
            'image_fit': 'cover',
            'meta_text': 'Updated stock note',
            'is_active': 'on',
            'start_date': '2026-08-05',
            'end_date': '2026-09-05',
            '_save': 'Save',
        }, follow=False)
        self.assertEqual(response.status_code, 302)
        offer.refresh_from_db()
        self.assertEqual(offer.title, 'Dry Season Deal Updated')
        self.assertEqual(offer.image_fit, 'cover')
        self.assertEqual(offer.badge_tone, 'brand')

        delete_url = reverse('admin:core_discountannouncement_delete', args=[offer.pk])
        response = self.client.post(delete_url, {'post': 'yes'}, follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(DiscountAnnouncement.objects.filter(pk=offer.pk).exists())

    def test_company_info_singleton_admin_behavior(self):
        add_url = reverse('admin:core_companyinfo_add')
        response = self.client.post(add_url, {
            'mission': 'Mission 1',
            'vision': 'Vision 1',
            'values': 'Values 1',
            '_save': 'Save',
        }, follow=False)
        self.assertEqual(response.status_code, 302)
        info = CompanyInfo.objects.get()

        change_url = reverse('admin:core_companyinfo_change', args=[info.pk])
        response = self.client.post(change_url, {
            'mission': 'Mission 2',
            'vision': 'Vision 2',
            'values': 'Values 2',
            '_save': 'Save',
        }, follow=False)
        self.assertEqual(response.status_code, 302)
        info.refresh_from_db()
        self.assertEqual(info.mission, 'Mission 2')

        response = self.client.get(add_url)
        self.assertEqual(response.status_code, 403)

    def test_contact_info_singleton_admin_behavior(self):
        add_url = reverse('admin:core_contactinfo_add')
        response = self.client.post(add_url, {
            'email': 'trade@example.com',
            'phone': '+8801700000000',
            'address': 'Dhaka, Bangladesh',
            'social_media_links': '[]',
            '_save': 'Save',
        }, follow=False)
        self.assertEqual(response.status_code, 302)
        info = ContactInfo.objects.get()

        change_url = reverse('admin:core_contactinfo_change', args=[info.pk])
        response = self.client.post(change_url, {
            'email': 'sales@example.com',
            'phone': '+8801711111111',
            'address': 'Chattogram, Bangladesh',
            'social_media_links': '["https://facebook.com/example"]',
            '_save': 'Save',
        }, follow=False)
        self.assertEqual(response.status_code, 302)
        info.refresh_from_db()
        self.assertEqual(info.email, 'sales@example.com')
        self.assertEqual(info.social_media_links, ['https://facebook.com/example'])

        response = self.client.get(add_url)
        self.assertEqual(response.status_code, 403)
