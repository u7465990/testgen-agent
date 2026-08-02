package com.demo;

import com.demo.BankAccount;
import org.junit.Assert;
import org.junit.Test;

public class BankAccount_deposit_Dbl_Test_Normal_4 {


    @Test
    public void deposit_withTypicalValues_updatesBalanceAndRejectsNonPositive() {
        BankAccount account = new BankAccount("Test Owner", 0.0);

        account.deposit(1.0);
        Assert.assertEquals(1.0, balanceOf(account), 0.000001);

        try {
            account.deposit(0.0);
            Assert.fail("Expected IllegalArgumentException for deposit of 0.0");
        } catch (IllegalArgumentException e) {
            Assert.assertEquals("Deposit must be positive", e.getMessage());
        }
        Assert.assertEquals(1.0, balanceOf(account), 0.000001);

        try {
            account.deposit(-1.0);
            Assert.fail("Expected IllegalArgumentException for deposit of -1.0");
        } catch (IllegalArgumentException e) {
            Assert.assertEquals("Deposit must be positive", e.getMessage());
        }
        Assert.assertEquals(1.0, balanceOf(account), 0.000001);
    }

    private static double balanceOf(BankAccount account) {
        try {
            java.lang.reflect.Field field = BankAccount.class.getDeclaredField("balance");
            field.setAccessible(true);
            return ((Number) field.get(account)).doubleValue();
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }

}