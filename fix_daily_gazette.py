# Fix daily gazette to send to all users regardless of subscription status

with open('core/management/commands/send_daily_gazette.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the subscription check logic with simple email collection
old_logic = '''                # Admin kullanıcılar her zaman dahil
                if user.is_staff or user.is_superuser:
                    active_emails.append(user.email)
                    continue
                
                try:
                    profile = user.userprofile
                    now = datetime.now().date()
                    
                    # Ücretsiz deneme kontrolü
                    if profile.free_trial_start_date:
                        trial_end = profile.free_trial_start_date + timedelta(days=60)
                        if now <= trial_end:
                            active_emails.append(user.email)
                            continue
                    
                    # Ücretli abonelik kontrolü
                    if hasattr(profile, 'subscription') and profile.subscription:
                        if profile.subscription.end_date and now <= profile.subscription.end_date:
                            active_emails.append(user.email)
                            continue
                
                except UserProfile.DoesNotExist:
                    # Profile yoksa skip et
                    continue
                except Exception as e:
                    logger.warning(f"Kullanıcı {user.username} kontrolü hatası: {e}")
                    continue'''

new_logic = '''                # Tüm kayıtlı kullanıcılara resmi gazete gönder
                active_emails.append(user.email)'''

content = content.replace(old_logic, new_logic)

with open('core/management/commands/send_daily_gazette.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Daily gazette service updated to send to all users')
